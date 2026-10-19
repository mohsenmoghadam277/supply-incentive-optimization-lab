"""Create a lightweight score-population drift snapshot; this is not live production monitoring."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import DATA_DIR, NUMERIC_FEATURES, OUTPUT_DIR


def _psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float | None:
    ref = pd.to_numeric(reference, errors="coerce").dropna().to_numpy()
    cur = pd.to_numeric(current, errors="coerce").dropna().to_numpy()
    if len(ref) < bins * 2 or len(cur) == 0:
        return None
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_counts = np.histogram(ref, bins=edges)[0].astype(float)
    cur_counts = np.histogram(cur, bins=edges)[0].astype(float)
    ref_pct = np.clip(ref_counts / ref_counts.sum(), 1e-6, None)
    cur_pct = np.clip(cur_counts / cur_counts.sum(), 1e-6, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def make_monitoring_snapshot(reference: pd.DataFrame, candidates: pd.DataFrame, scored: pd.DataFrame, output_path: Path = OUTPUT_DIR / "monitoring_snapshot.json") -> dict:
    features = {}
    for col in NUMERIC_FEATURES:
        val = _psi(reference[col], candidates[col])
        if val is None:
            level = "insufficient_data"
        elif val < 0.10:
            level = "low"
        elif val < 0.25:
            level = "moderate"
        else:
            level = "high"
        features[col] = {"psi": val, "drift_level": level}
    uplift = pd.to_numeric(scored["predicted_incremental_trips"], errors="coerce")
    payload = {
        "classification": "synthetic offline baseline snapshot; not connected to a live production system",
        "candidate_rows": int(len(candidates)),
        "scored_rows": int(len(scored)),
        "predicted_uplift": {
            "mean": float(uplift.mean()),
            "median": float(uplift.median()),
            "p05": float(uplift.quantile(0.05)),
            "p95": float(uplift.quantile(0.95)),
            "negative_score_rate": float((uplift < 0).mean()),
        },
        "numeric_feature_psi": features,
        "thresholds": {"low": "PSI < 0.10", "moderate": "0.10 <= PSI < 0.25", "high": "PSI >= 0.25"},
        "monitoring_gaps": [
            "No production traffic or delayed outcome data is connected.",
            "Outcome-model MAE/RMSE and causal policy performance must be monitored after outcomes mature.",
            "PSI is a triage signal, not proof of material model degradation.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
