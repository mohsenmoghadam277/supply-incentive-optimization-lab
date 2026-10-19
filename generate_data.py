"""Generate reproducible, explicitly synthetic experiment and candidate datasets."""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from src.config import (
    CAMPAIGN_ID, CONTROL_N, DATA_DIR, N_CANDIDATES, N_EXPERIMENT_DRIVERS,
    SEED, TREATMENT_N, ZONE_VALUES, DAYPART_VALUES,
)

ZONE_P = [0.28, 0.16, 0.18, 0.18, 0.20]
DAYPART_P = [0.25, 0.25, 0.35, 0.15]


def _features(n: int, rng: np.random.Generator, start_id: int) -> pd.DataFrame:
    zone = rng.choice(ZONE_VALUES, n, p=ZONE_P)
    daypart = rng.choice(DAYPART_VALUES, n, p=DAYPART_P)
    avg_trips = np.clip(rng.normal(41.5, 12.0, n), 2, 85)
    online_hours = np.clip(rng.normal(16.5, 5.8, n), 1, 42)
    cancellation = np.clip(rng.beta(2.2, 18.0, n), 0.005, 0.45)
    acceptance = np.clip(rng.beta(15.0, 3.5, n), 0.30, 0.995)
    demand = np.clip(rng.normal(0.86, 0.16, n), 0.35, 1.35)
    tenure = np.clip(rng.lognormal(mean=5.2, sigma=0.9, size=n), 7, 2_500)
    is_active = rng.binomial(1, np.clip(0.72 + 0.005 * np.minimum(online_hours, 30), 0.7, 0.94), n)
    return pd.DataFrame({
        "driver_id": [f"D{i:06d}" for i in range(start_id, start_id + n)],
        "campaign_id": CAMPAIGN_ID,
        "zone": zone,
        "daypart": daypart,
        "avg_online_hours_4w": np.round(online_hours, 2),
        "avg_trips_4w": np.round(avg_trips, 2),
        "cancellation_rate": np.round(cancellation, 4),
        "demand_index": np.round(demand, 3),
        "acceptance_rate": np.round(acceptance, 4),
        "tenure_days": np.round(tenure).astype(int),
        "is_active_pre": is_active.astype(int),
    })


def _baseline_and_uplift(df: pd.DataFrame, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    zone_baseline = {"central": 1.2, "east": 0.4, "north": 0.2, "south": -1.0, "west": -0.3}
    daypart_baseline = {"morning": 0.8, "afternoon": -0.5, "evening": 0.5, "late_night": -0.1}
    tau_daypart = {"morning": 3.20, "afternoon": 1.05, "evening": 2.05, "late_night": 3.45}
    tau_zone = {"central": 0.20, "east": 0.10, "north": 0.00, "south": -0.28, "west": -0.08}
    baseline = (
        13.0
        + 0.58 * df["avg_trips_4w"].to_numpy()
        + 0.25 * df["avg_online_hours_4w"].to_numpy()
        + 4.0 * (df["demand_index"].to_numpy() - 0.86)
        + df["zone"].map(zone_baseline).to_numpy()
        + df["daypart"].map(daypart_baseline).to_numpy()
        + 3.0 * (df["acceptance_rate"].to_numpy() - 0.80)
        - 7.0 * (df["cancellation_rate"].to_numpy() - 0.10)
        + 0.7 * np.log1p(df["tenure_days"].to_numpy() / 30.0)
    )
    uplift = (
        df["daypart"].map(tau_daypart).to_numpy()
        + df["zone"].map(tau_zone).to_numpy()
        + 1.5 * (df["demand_index"].to_numpy() - 0.86)
        + 1.1 * (df["acceptance_rate"].to_numpy() - 0.80)
        - 1.6 * (df["cancellation_rate"].to_numpy() - 0.10)
        + 0.18 * (df["is_active_pre"].to_numpy() - 0.8)
    )
    # Center the heterogeneity around a portfolio-level mean of 2.30 trips.
    uplift = uplift - (float(np.mean(uplift)) - 2.30)
    return baseline, np.clip(uplift, 0.25, 5.5)


def generate_datasets(output_dir: Path = DATA_DIR, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write a randomized historical experiment and a no-outcome scoring pool."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    exp = _features(N_EXPERIMENT_DRIVERS, rng, start_id=1)
    baseline, true_uplift = _baseline_and_uplift(exp, rng)
    assignment = np.array([1] * TREATMENT_N + [0] * CONTROL_N, dtype=np.int8)
    rng.shuffle(assignment)
    exp["treatment"] = assignment
    # Outcome noise deliberately remains large relative to individual effects.
    noise = rng.normal(0, 7.2, N_EXPERIMENT_DRIVERS)
    observed_mean = baseline + exp["treatment"].to_numpy() * true_uplift + noise
    exp["trips_next_week"] = np.rint(np.clip(observed_mean, 0, None)).astype(int)

    online_noise = rng.normal(0, 3.2, N_EXPERIMENT_DRIVERS)
    exp["online_hours_next_week"] = np.round(
        np.clip(
            exp["avg_online_hours_4w"].to_numpy() * 0.78
            + 3.0
            + exp["treatment"].to_numpy() * (0.45 + 0.30 * true_uplift)
            + online_noise,
            0, 70,
        ), 2
    )
    p_active = np.clip(
        0.72 + 0.0045 * exp["avg_online_hours_4w"].to_numpy()
        + 0.10 * exp["is_active_pre"].to_numpy()
        + exp["treatment"].to_numpy() * 0.045,
        0.02, 0.99,
    )
    exp["active_next_week"] = rng.binomial(1, p_active).astype(int)

    cost_base = (
        85_000
        + exp["daypart"].map({"morning": 1_000, "afternoon": -2_500, "evening": 1_500, "late_night": 2_000}).to_numpy()
        + exp["zone"].map({"central": 1_500, "east": 500, "north": 0, "south": -1_500, "west": -200}).to_numpy()
        + rng.normal(0, 5_000, N_EXPERIMENT_DRIVERS)
    )
    exp["incentive_cost_toman"] = np.where(exp["treatment"].to_numpy() == 1, np.maximum(25_000, np.rint(cost_base)), 0).astype(int)
    exp["assignment_date"] = "2026-09-01"
    exp["synthetic_data"] = 1
    # Intentionally do not write true_uplift: it is generator-only and unavailable in production.

    candidates = _features(N_CANDIDATES, rng, start_id=20_001)
    candidates["scoring_date"] = "2026-10-19"
    candidates["synthetic_data"] = 1

    exp_path = output_dir / "experiment_data.csv"
    candidate_path = output_dir / "candidate_pool.csv"
    exp.to_csv(exp_path, index=False, encoding="utf-8-sig")
    candidates.to_csv(candidate_path, index=False, encoding="utf-8-sig")
    return exp, candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    exp, candidates = generate_datasets(args.output_dir, args.seed)
    print(f"Synthetic experiment: {len(exp):,} drivers; treatment={int(exp.treatment.sum()):,}; control={int((1-exp.treatment).sum()):,}")
    print(f"Synthetic scoring pool: {len(candidates):,} drivers")
    print(f"Written to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
