"""Statistical analysis and campaign unit economics for a randomized experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

from src.config import ASSUMED_GROSS_MARGIN_TOMAN, DATA_DIR, OUTPUT_DIR, SEED

METRICS = ["trips_next_week", "online_hours_next_week", "active_next_week"]


def _welch_result(treated: pd.Series, control: pd.Series) -> dict[str, float | None]:
    a = treated.dropna().astype(float).to_numpy()
    b = control.dropna().astype(float).to_numpy()
    diff = float(a.mean() - b.mean())
    va, vb = float(a.var(ddof=1)), float(b.var(ddof=1))
    se2 = va / len(a) + vb / len(b)
    se = float(np.sqrt(se2))
    df_num = se2**2
    df_den = (va / len(a))**2 / max(len(a) - 1, 1) + (vb / len(b))**2 / max(len(b) - 1, 1)
    dof = df_num / df_den if df_den > 0 else float("inf")
    crit = float(stats.t.ppf(0.975, dof))
    test = stats.ttest_ind(a, b, equal_var=False, nan_policy="omit")
    return {
        "difference_treatment_minus_control": diff,
        "ci95_low": diff - crit * se,
        "ci95_high": diff + crit * se,
        "p_value_welch": float(test.pvalue),
        "standard_error": se,
        "n_treatment": int(len(a)),
        "n_control": int(len(b)),
    }


def analyze_experiment(data: pd.DataFrame, output_dir: Path = OUTPUT_DIR, margin_per_trip: float = ASSUMED_GROSS_MARGIN_TOMAN) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    treatment = data.loc[data["treatment"] == 1]
    control = data.loc[data["treatment"] == 0]
    rows: list[dict] = []
    for metric in METRICS:
        a, b = treatment[metric], control[metric]
        result = _welch_result(a, b)
        rows.append({
            "metric": metric,
            "treatment_mean": float(a.mean()),
            "control_mean": float(b.mean()),
            **result,
        })

    treated_cost = treatment["incentive_cost_toman"].astype(float)
    avg_cost = float(treated_cost.mean())
    # Cost is a treatment delivery/accounting variable, not an outcome for significance testing.
    rows.append({
        "metric": "incentive_cost_toman",
        "treatment_mean": avg_cost,
        "control_mean": 0.0,
        "difference_treatment_minus_control": avg_cost,
        "ci95_low": None,
        "ci95_high": None,
        "p_value_welch": None,
        "standard_error": None,
        "n_treatment": int(len(treatment)),
        "n_control": int(len(control)),
    })
    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir / "experiment_summary.csv", index=False, encoding="utf-8-sig")

    # Secondary robustness check: covariate-adjusted OLS with heteroskedasticity-robust HC3 errors.
    # The unadjusted randomized ITT remains the primary reported estimate.
    formula = (
        "trips_next_week ~ treatment + avg_trips_4w + avg_online_hours_4w + "
        "cancellation_rate + demand_index + acceptance_rate + tenure_days + is_active_pre + C(zone) + C(daypart)"
    )
    adjustment_columns = [
        "trips_next_week", "treatment", "avg_trips_4w", "avg_online_hours_4w",
        "cancellation_rate", "demand_index", "acceptance_rate", "tenure_days",
        "is_active_pre", "zone", "daypart",
    ]
    missing_adjustment_columns = sorted(set(adjustment_columns) - set(data.columns))
    if missing_adjustment_columns or len(data) < 100:
        # Small, intentionally minimal unit-test frames may not contain the complete adjustment set.
        adjusted_result = {
            "classification": "synthetic_educational_data",
            "status": "skipped",
            "reason": (
                f"Missing adjustment columns: {missing_adjustment_columns}"
                if missing_adjustment_columns else "Insufficient rows for a stable covariate-adjusted robustness check"
            ),
            "formula": formula,
            "interpretation_note": "The unadjusted randomized ATE is still computed; adjusted OLS is a secondary robustness check.",
        }
    else:
        adjusted = smf.ols(formula, data=data).fit(cov_type="HC3")
        effect = float(adjusted.params["treatment"])
        conf = adjusted.conf_int().loc["treatment"]
        adjusted_result = {
            "classification": "synthetic_educational_data",
            "status": "completed",
            "model": "OLS with pre-treatment covariates and HC3 robust standard errors",
            "treatment_coefficient_trips": effect,
            "robust_standard_error": float(adjusted.bse["treatment"]),
            "ci95_low": float(conf.iloc[0]),
            "ci95_high": float(conf.iloc[1]),
            "p_value": float(adjusted.pvalues["treatment"]),
            "n": int(adjusted.nobs),
            "formula": formula,
            "interpretation_note": "Secondary robustness check only; unadjusted randomized ATE remains primary. This does not validate individual treatment-effect predictions.",
        }
    (output_dir / "adjusted_effect_check.json").write_text(json.dumps(adjusted_result, ensure_ascii=False, indent=2), encoding="utf-8")

    segments: list[dict] = []
    for key in ["zone", "daypart"]:
        for segment, grp in data.groupby(key, observed=True):
            a = grp.loc[grp.treatment == 1]
            b = grp.loc[grp.treatment == 0]
            if len(a) == 0 or len(b) == 0:
                continue
            result = _welch_result(a["trips_next_week"], b["trips_next_week"])
            lift = result["difference_treatment_minus_control"]
            cost = float(a["incentive_cost_toman"].mean())
            segments.append({
                "segment_by": key,
                "segment": str(segment),
                "treatment_n": int(len(a)),
                "control_n": int(len(b)),
                "trip_lift": float(lift),
                "ci95_low": result["ci95_low"],
                "ci95_high": result["ci95_high"],
                "p_value_welch": result["p_value_welch"],
                "incremental_cost_per_driver_toman": cost,
                "cost_per_incremental_trip_toman": cost / lift if lift > 0 else None,
            })
    segment_df = pd.DataFrame(segments)
    segment_df.to_csv(output_dir / "segment_summary.csv", index=False, encoding="utf-8-sig")

    trip_row = summary.loc[summary.metric == "trips_next_week"].iloc[0]
    lift = float(trip_row["difference_treatment_minus_control"])
    gross = lift * float(margin_per_trip)
    net = gross - avg_cost
    roi = net / avg_cost if avg_cost > 0 else None
    economics = {
        "data_classification": "synthetic_educational_data",
        "rows": int(len(data)),
        "treatment_n": int(len(treatment)),
        "control_n": int(len(control)),
        "trip_lift_per_assigned_driver": lift,
        "trip_lift_ci95_low": float(trip_row["ci95_low"]),
        "trip_lift_ci95_high": float(trip_row["ci95_high"]),
        "incremental_cost_per_assigned_driver_toman": avg_cost,
        "assumed_gross_margin_per_trip_toman": float(margin_per_trip),
        "estimated_incremental_value_per_treated_driver_toman": gross,
        "estimated_net_value_per_treated_driver_toman": net,
        "estimated_roi": roi,
        "break_even_gross_margin_per_trip_toman": avg_cost / lift if lift > 0 else None,
        "interpretation_note": "Synthetic data only. ROI is an illustrative scenario based on an assumed gross margin per incremental trip; it is not Snapp performance.",
        "cost_note": "Average incentive cost among treated drivers; control costs are zero by design. Cost is descriptive and is not tested as an outcome.",
    }
    (output_dir / "campaign_economics.json").write_text(json.dumps(economics, ensure_ascii=False, indent=2), encoding="utf-8")

    sensitivity = []
    for margin in [25_000, 35_000, 40_000, 50_000, 60_000, 75_000]:
        gross_value = lift * margin
        net_value = gross_value - avg_cost
        sensitivity.append({
            "assumed_gross_margin_per_trip_toman": margin,
            "estimated_gross_incremental_value_per_treated_driver_toman": gross_value,
            "estimated_net_value_per_treated_driver_toman": net_value,
            "estimated_roi": net_value / avg_cost if avg_cost else None,
        })
    pd.DataFrame(sensitivity).to_csv(output_dir / "economics_sensitivity.csv", index=False, encoding="utf-8-sig")
    return {"summary": summary, "segments": segment_df, "economics": economics, "adjusted": adjusted_result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA_DIR / "experiment_data.csv")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--margin-per-trip", type=float, default=ASSUMED_GROSS_MARGIN_TOMAN)
    args = parser.parse_args()
    data = pd.read_csv(args.input)
    result = analyze_experiment(data, args.output_dir, args.margin_per_trip)
    economics = result["economics"]
    print("A/B test analysis completed (synthetic data)")
    print(f"Trip lift: {economics['trip_lift_per_assigned_driver']:.3f} trips (95% CI {economics['trip_lift_ci95_low']:.3f}, {economics['trip_lift_ci95_high']:.3f})")
    print(f"Assumed margin: {args.margin_per_trip:,.0f} toman/trip | scenario ROI: {economics['estimated_roi']:.1%}")
    print(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
