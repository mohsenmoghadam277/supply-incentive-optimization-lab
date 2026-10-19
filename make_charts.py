"""Render source-backed static QA figures from the generated project outputs."""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from src.config import OUTPUT_DIR


def make_charts(output_dir: Path = OUTPUT_DIR) -> list[Path]:
    figures = output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    summary = pd.read_csv(output_dir / "experiment_summary.csv")
    econ = json.loads((output_dir / "campaign_economics.json").read_text(encoding="utf-8"))
    trip = summary.loc[summary.metric == "trips_next_week"].iloc[0]

    fig, ax = plt.subplots(figsize=(8, 5))
    estimate = float(trip.difference_treatment_minus_control)
    low = float(trip.ci95_low)
    high = float(trip.ci95_high)
    ax.errorbar([estimate], ["Randomized A/B"], xerr=[[estimate - low], [high - estimate]], fmt="o", capsize=6)
    ax.axvline(0, linestyle="--", linewidth=1)
    ax.set_xlabel("Incremental trips per assigned driver (95% CI)")
    ax.set_title("Primary A/B estimate — synthetic experiment")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    path = figures / "experiment_lift_ci.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    created.append(path)

    segments = pd.read_csv(output_dir / "segment_summary.csv")
    day = segments[(segments.segment_by == "daypart") & segments.cost_per_incremental_trip_toman.notna()].sort_values("cost_per_incremental_trip_toman")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(day.segment, day.cost_per_incremental_trip_toman)
    ax.set_xlabel("Toman per observed incremental trip (illustrative)")
    ax.set_title("Observed segment economics — exploratory synthetic data")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    path = figures / "daypart_cost_per_incremental_trip.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    created.append(path)

    deciles = pd.read_csv(output_dir / "uplift_decile_summary.csv")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(deciles.score_decile, deciles.mean_predicted_uplift, marker="o", label="Mean predicted uplift")
    ax.plot(deciles.score_decile, deciles.observed_trip_lift, marker="s", label="Observed randomized-arm difference")
    ax.fill_between(deciles.score_decile, deciles.ci95_low, deciles.ci95_high, alpha=0.15, label="Observed 95% CI")
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xlabel("Score decile (1 = highest predicted uplift)")
    ax.set_ylabel("Trips per driver")
    ax.set_title("Uplift ranking validation on held-out randomized data")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = figures / "uplift_decile_validation.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    created.append(path)

    sens = pd.read_csv(output_dir / "economics_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sens.assumed_gross_margin_per_trip_toman, sens.estimated_roi * 100, marker="o")
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xlabel("Assumed gross margin per incremental trip (toman)")
    ax.set_ylabel("Scenario ROI (%)")
    ax.set_title("Campaign economics sensitivity — not actual company ROI")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = figures / "roi_sensitivity.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    created.append(path)
    return created
