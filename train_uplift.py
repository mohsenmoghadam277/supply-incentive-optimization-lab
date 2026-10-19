"""Train and validate a T-learner for incremental trip prediction (synthetic portfolio project)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.analyze_experiment import _welch_result
from src.config import (
    ARTIFACT_DIR, ASSUMED_GROSS_MARGIN_TOMAN, CATEGORICAL_FEATURES, COST_COL,
    DATA_DIR, FEATURES, NUMERIC_FEATURES, OUTCOME_TRIPS, OUTPUT_DIR, SEED,
    TOP_K_FRACTION,
)


def build_outcome_model(seed: int) -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric, NUMERIC_FEATURES),
        ("cat", categorical, CATEGORICAL_FEATURES),
    ])
    regressor = RandomForestRegressor(
        n_estimators=120,
        max_depth=10,
        min_samples_leaf=25,
        max_features=0.9,
        n_jobs=-1,
        random_state=seed,
    )
    return Pipeline([("preprocess", preprocessor), ("model", regressor)])


def _fit_t_learner(train: pd.DataFrame, seed: int) -> tuple[Pipeline, Pipeline]:
    control = train.loc[train["treatment"] == 0]
    treatment = train.loc[train["treatment"] == 1]
    if len(control) < 50 or len(treatment) < 50:
        raise ValueError("Both randomized arms need at least 50 rows to train the two outcome models.")
    m0 = build_outcome_model(seed)
    m1 = build_outcome_model(seed + 1)
    m0.fit(control[FEATURES], control[OUTCOME_TRIPS])
    m1.fit(treatment[FEATURES], treatment[OUTCOME_TRIPS])
    return m0, m1


def _score_features(df: pd.DataFrame, m0: Pipeline, m1: Pipeline) -> pd.DataFrame:
    pred0 = m0.predict(df[FEATURES])
    pred1 = m1.predict(df[FEATURES])
    return pd.DataFrame({
        "predicted_trips_without_incentive": pred0,
        "predicted_trips_with_incentive": pred1,
        "predicted_incremental_trips": pred1 - pred0,
    }, index=df.index)


def _model_metrics(test: pd.DataFrame, pred: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    metrics: dict[str, float | int | str] = {
        "data_classification": "synthetic_educational_data",
        "evaluation_design": "random 20% holdout stratified by randomized treatment assignment",
        "test_n": int(len(test)),
        "test_treatment_n": int((test.treatment == 1).sum()),
        "test_control_n": int((test.treatment == 0).sum()),
    }
    for name, mask in [("control", test.treatment == 0), ("treatment", test.treatment == 1)]:
        y = test.loc[mask, OUTCOME_TRIPS].to_numpy()
        yhat = (pred.loc[mask, "predicted_trips_without_incentive"] if name == "control" else pred.loc[mask, "predicted_trips_with_incentive"]).to_numpy()
        metrics[f"{name}_test_mae_trips"] = float(mean_absolute_error(y, yhat))
        metrics[f"{name}_test_rmse_trips"] = float(np.sqrt(mean_squared_error(y, yhat)))
        metrics[f"{name}_test_r2"] = float(r2_score(y, yhat))

    all_diff = _welch_result(
        test.loc[test.treatment == 1, OUTCOME_TRIPS],
        test.loc[test.treatment == 0, OUTCOME_TRIPS],
    )
    metrics.update({
        "observed_test_trip_lift_all": all_diff["difference_treatment_minus_control"],
        "observed_test_trip_lift_ci95_low": all_diff["ci95_low"],
        "observed_test_trip_lift_ci95_high": all_diff["ci95_high"],
        "observed_test_trip_lift_p_value": all_diff["p_value_welch"],
        "mean_predicted_uplift_test": float(pred["predicted_incremental_trips"].mean()),
    })

    ranked_idx = pred["predicted_incremental_trips"].sort_values(ascending=False).index
    top_n = max(1, int(np.ceil(len(test) * TOP_K_FRACTION)))
    top_idx = ranked_idx[:top_n]
    bottom_idx = ranked_idx[-top_n:]
    for label, idx in [("top20", top_idx), ("bottom20", bottom_idx)]:
        cohort = test.loc[idx]
        res = _welch_result(cohort.loc[cohort.treatment == 1, OUTCOME_TRIPS], cohort.loc[cohort.treatment == 0, OUTCOME_TRIPS])
        metrics[f"{label}_observed_trip_lift"] = res["difference_treatment_minus_control"]
        metrics[f"{label}_observed_trip_lift_ci95_low"] = res["ci95_low"]
        metrics[f"{label}_observed_trip_lift_ci95_high"] = res["ci95_high"]
        metrics[f"{label}_predicted_uplift"] = float(pred.loc[idx, "predicted_incremental_trips"].mean())
        metrics[f"{label}_test_n"] = int(len(cohort))
        metrics[f"{label}_treatment_n"] = int((cohort.treatment == 1).sum())
        metrics[f"{label}_control_n"] = int((cohort.treatment == 0).sum())

    scored_test = test[["driver_id", "treatment", OUTCOME_TRIPS]].copy()
    scored_test["predicted_uplift"] = pred["predicted_incremental_trips"]
    scored_test = scored_test.sort_values("predicted_uplift", ascending=False).reset_index(drop=True)
    scored_test["score_decile"] = np.minimum(np.floor(np.arange(len(scored_test)) / max(1, len(scored_test) / 10)).astype(int) + 1, 10)
    decile_rows = []
    for decile, g in scored_test.groupby("score_decile", sort=True):
        t = g[g.treatment == 1][OUTCOME_TRIPS]
        c = g[g.treatment == 0][OUTCOME_TRIPS]
        observed = _welch_result(t, c) if len(t) and len(c) else {}
        decile_rows.append({
            "score_decile": int(decile),
            "score_band": "top" if decile == 1 else "bottom" if decile == 10 else "middle",
            "test_n": int(len(g)),
            "treatment_n": int(len(t)),
            "control_n": int(len(c)),
            "mean_predicted_uplift": float(g.predicted_uplift.mean()),
            "observed_trip_lift": observed.get("difference_treatment_minus_control"),
            "ci95_low": observed.get("ci95_low"),
            "ci95_high": observed.get("ci95_high"),
            "p_value_welch": observed.get("p_value_welch"),
        })
    return metrics, pd.DataFrame(decile_rows)


def train_and_score(experiment: pd.DataFrame, candidates: pd.DataFrame, output_dir: Path = OUTPUT_DIR, artifact_dir: Path = ARTIFACT_DIR, seed: int = SEED, margin_per_trip: float = ASSUMED_GROSS_MARGIN_TOMAN) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    required_exp = set(FEATURES + ["treatment", OUTCOME_TRIPS, COST_COL, "driver_id"])
    required_cand = set(FEATURES + ["driver_id"])
    if missing := required_exp - set(experiment.columns):
        raise ValueError(f"Experiment data is missing required fields: {sorted(missing)}")
    if missing := required_cand - set(candidates.columns):
        raise ValueError(f"Candidate pool is missing required fields: {sorted(missing)}")
    if experiment[FEATURES].isna().all(axis=1).any():
        raise ValueError("At least one experiment row has all model features missing.")

    train, test = train_test_split(experiment, test_size=0.20, random_state=seed, stratify=experiment["treatment"])
    m0_holdout, m1_holdout = _fit_t_learner(train, seed)
    test_pred = _score_features(test, m0_holdout, m1_holdout)
    model_metrics, deciles = _model_metrics(test, test_pred)
    model_metrics["train_n"] = int(len(train))
    model_metrics["test_fraction"] = 0.20
    model_metrics["model_type"] = "T-learner: separate RandomForestRegressor for treatment and control outcomes"
    model_metrics["note"] = "Outcome prediction metrics do not establish individual causal uplift. The randomized holdout gives a noisy cohort-level check; targeting should be tested prospectively."
    (output_dir / "model_validation.json").write_text(json.dumps(model_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    deciles.to_csv(output_dir / "uplift_decile_summary.csv", index=False, encoding="utf-8-sig")

    # Refit both potential-outcome models on the complete randomized experiment for scoring a separate, unlabeled candidate pool.
    m0_final, m1_final = _fit_t_learner(experiment, seed + 100)
    scored = candidates.copy()
    predictions = _score_features(scored, m0_final, m1_final)
    scored = pd.concat([scored.reset_index(drop=True), predictions.reset_index(drop=True)], axis=1)
    exp_cost = float(experiment.loc[experiment.treatment == 1, COST_COL].mean())
    scored["assumed_expected_cost_toman"] = exp_cost
    scored["predicted_incremental_trips_per_100k_toman"] = (
        scored["predicted_incremental_trips"] / exp_cost * 100_000.0 if exp_cost > 0 else np.nan
    )
    scored["expected_net_value_toman"] = scored["predicted_incremental_trips"] * float(margin_per_trip) - exp_cost
    scored = scored.sort_values(["expected_net_value_toman", "predicted_incremental_trips"], ascending=False).reset_index(drop=True)
    top_n = max(1, int(np.ceil(len(scored) * TOP_K_FRACTION)))
    scored["recommendation_rank"] = np.arange(1, len(scored) + 1)
    scored["recommended_for_top_20pct"] = (scored["recommendation_rank"] <= top_n).astype(int)
    # Keep exactly the columns consumed by the existing interactive dashboard plus review-friendly additions.
    scored.to_csv(output_dir / "scored_candidates.csv", index=False, encoding="utf-8-sig")
    scored.to_csv(output_dir / "uplift_recommendations.csv", index=False, encoding="utf-8-sig")

    # Feature importance is predictive, not causal feature attribution.
    names0 = m0_final.named_steps["preprocess"].get_feature_names_out()
    names1 = m1_final.named_steps["preprocess"].get_feature_names_out()
    imp0 = pd.Series(m0_final.named_steps["model"].feature_importances_, index=names0)
    imp1 = pd.Series(m1_final.named_steps["model"].feature_importances_, index=names1)
    importance = pd.concat([imp0.rename("control_importance"), imp1.rename("treatment_importance")], axis=1).fillna(0)
    importance["mean_importance"] = importance[["control_importance", "treatment_importance"]].mean(axis=1)
    importance.sort_values("mean_importance", ascending=False).to_csv(output_dir / "feature_importance.csv", encoding="utf-8-sig")

    bundle = {
        "control_model": m0_final,
        "treatment_model": m1_final,
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "expected_cost_toman": exp_cost,
        "margin_per_trip_toman": float(margin_per_trip),
        "training_rows": int(len(experiment)),
        "model_version": "t_learner_rf_v1",
        "synthetic_data_only": True,
    }
    joblib.dump(bundle, artifact_dir / "uplift_model.joblib", compress=3)

    result = {
        "validation": model_metrics,
        "recommendations": scored,
        "feature_importance": importance.sort_values("mean_importance", ascending=False),
        "model_bundle_path": str((artifact_dir / "uplift_model.joblib").resolve()),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DATA_DIR / "experiment_data.csv")
    parser.add_argument("--candidates", type=Path, default=DATA_DIR / "candidate_pool.csv")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--margin-per-trip", type=float, default=ASSUMED_GROSS_MARGIN_TOMAN)
    args = parser.parse_args()
    exp, cand = pd.read_csv(args.experiment), pd.read_csv(args.candidates)
    result = train_and_score(exp, cand, args.output_dir, args.artifact_dir, args.seed, args.margin_per_trip)
    v = result["validation"]
    print("T-learner training completed (synthetic data)")
    print(f"Control MAE={v['control_test_mae_trips']:.3f} | Treatment MAE={v['treatment_test_mae_trips']:.3f}")
    print(f"Holdout observed lift={v['observed_test_trip_lift_all']:.3f} | top-20% observed lift={v['top20_observed_trip_lift']:.3f}")
    print(f"Scored candidates={len(result['recommendations']):,}; top-20% recommendations={int(result['recommendations']['recommended_for_top_20pct'].sum()):,}")
    print(f"Model artifact: {result['model_bundle_path']}")


if __name__ == "__main__":
    main()
