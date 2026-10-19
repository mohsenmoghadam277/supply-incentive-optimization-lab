"""Input data-quality gates for the offline incentive pipeline."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from src.config import FEATURES, OUTCOME_TRIPS, COST_COL, OUTPUT_DIR


def validate_datasets(experiment: pd.DataFrame, candidates: pd.DataFrame, output_path: Path = OUTPUT_DIR / "data_quality_report.json") -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    required_exp = set(FEATURES + ["driver_id", "campaign_id", "treatment", OUTCOME_TRIPS, COST_COL, "online_hours_next_week", "active_next_week", "synthetic_data"])
    required_cand = set(FEATURES + ["driver_id", "synthetic_data"])
    miss_exp = sorted(required_exp - set(experiment.columns))
    miss_cand = sorted(required_cand - set(candidates.columns))
    if miss_exp:
        errors.append(f"Experiment table missing required columns: {miss_exp}")
    if miss_cand:
        errors.append(f"Candidate table missing required columns: {miss_cand}")
    if errors:
        payload = {"status": "fail", "errors": errors, "warnings": warnings}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        raise ValueError("Input schema validation failed: " + "; ".join(errors))

    checks = {
        "experiment_rows": int(len(experiment)),
        "candidate_rows": int(len(candidates)),
        "duplicate_experiment_driver_ids": int(experiment["driver_id"].duplicated().sum()),
        "duplicate_candidate_driver_ids": int(candidates["driver_id"].duplicated().sum()),
        "experiment_missing_cells": int(experiment[sorted(required_exp)].isna().sum().sum()),
        "candidate_missing_cells": int(candidates[sorted(required_cand)].isna().sum().sum()),
        "treatment_n": int((experiment["treatment"] == 1).sum()),
        "control_n": int((experiment["treatment"] == 0).sum()),
        "invalid_treatment_values": int((~experiment["treatment"].isin([0, 1])).sum()),
        "control_rows_with_nonzero_cost": int(((experiment["treatment"] == 0) & (experiment[COST_COL] != 0)).sum()),
        "treated_rows_with_nonpositive_cost": int(((experiment["treatment"] == 1) & (experiment[COST_COL] <= 0)).sum()),
        "invalid_cancellation_rate_rows": int((~experiment["cancellation_rate"].between(0, 1)).sum()),
        "invalid_acceptance_rate_rows": int((~experiment["acceptance_rate"].between(0, 1)).sum()),
        "candidate_overlap_with_experiment_ids": int(experiment["driver_id"].isin(candidates["driver_id"]).sum()),
        "post_outcome_features_in_candidates": sorted(set([OUTCOME_TRIPS, "online_hours_next_week", "active_next_week", COST_COL, "treatment"]) & set(candidates.columns)),
        "non_synthetic_experiment_rows": int((experiment["synthetic_data"] != 1).sum()),
        "non_synthetic_candidate_rows": int((candidates["synthetic_data"] != 1).sum()),
    }
    for key, value in checks.items():
        if key.startswith("duplicate_") and value:
            errors.append(f"{key}={value}")
        if key.endswith("missing_cells") and value:
            errors.append(f"{key}={value}")
        if key in {"invalid_treatment_values", "control_rows_with_nonzero_cost", "treated_rows_with_nonpositive_cost", "invalid_cancellation_rate_rows", "invalid_acceptance_rate_rows", "candidate_overlap_with_experiment_ids", "non_synthetic_experiment_rows", "non_synthetic_candidate_rows"} and value:
            errors.append(f"{key}={value}")
        if key == "post_outcome_features_in_candidates" and value:
            errors.append(f"candidate leakage columns present: {value}")
    if experiment[FEATURES].isna().any().any() or candidates[FEATURES].isna().any().any():
        warnings.append("Model features contain missing values; the modeling pipeline imputes these at fit/inference time.")
    if (experiment[OUTCOME_TRIPS] < 0).any():
        errors.append("Negative next-week trip outcomes found.")

    payload = {
        "status": "pass" if not errors else "fail",
        "classification": "synthetic educational data",
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "notes": [
            "Candidate pool must not contain treatment assignment or post-assignment outcomes.",
            "A pass confirms local schema and basic logical integrity; it does not establish real-source validity or causal identification.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        raise ValueError("Data-quality checks failed: " + "; ".join(errors))
    return payload
