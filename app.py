"""Local inference API for the synthetic Incentive Lab T-learner model."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Annotated, Literal
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(os.getenv("UPLIFT_MODEL_PATH", ROOT / "artifacts" / "uplift_model.joblib"))

app = FastAPI(
    title="Incentive Uplift Scoring API",
    version="1.0.0",
    description="Portfolio demo only: estimates average outcome differences with a T-learner trained on synthetic randomized data.",
)
_bundle = None
if MODEL_PATH.exists():
    _bundle = joblib.load(MODEL_PATH)


class DriverFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    driver_id: str | None = Field(default=None, max_length=64)
    zone: Literal["central", "east", "north", "south", "west"]
    daypart: Literal["morning", "afternoon", "evening", "late_night"]
    avg_online_hours_4w: Annotated[float, Field(ge=0, le=100)]
    avg_trips_4w: Annotated[float, Field(ge=0, le=250)]
    cancellation_rate: Annotated[float, Field(ge=0, le=1)]
    demand_index: Annotated[float, Field(ge=0, le=3)]
    acceptance_rate: Annotated[float, Field(ge=0, le=1)]
    tenure_days: Annotated[int, Field(ge=0, le=10_000)]
    is_active_pre: Annotated[int, Field(ge=0, le=1)]


class BatchScoreRequest(BaseModel):
    drivers: list[DriverFeatures] = Field(min_length=1, max_length=500)


def _ensure_model() -> dict:
    if _bundle is None:
        raise HTTPException(status_code=503, detail="Model artifact not found. Run `python -m src.run_pipeline` first.")
    return _bundle


def _score_one(row: DriverFeatures, bundle: dict) -> dict:
    features = {key: getattr(row, key) for key in bundle["features"]}
    frame = pd.DataFrame([features], columns=bundle["features"])
    pred0 = float(bundle["control_model"].predict(frame)[0])
    pred1 = float(bundle["treatment_model"].predict(frame)[0])
    uplift = pred1 - pred0
    cost = float(bundle["expected_cost_toman"])
    margin = float(bundle["margin_per_trip_toman"])
    return {
        "driver_id": row.driver_id,
        "predicted_trips_without_incentive": round(pred0, 3),
        "predicted_trips_with_incentive": round(pred1, 3),
        "predicted_incremental_trips": round(uplift, 3),
        "assumed_expected_cost_toman": round(cost, 2),
        "assumed_margin_per_trip_toman": round(margin, 2),
        "expected_net_value_toman": round(uplift * margin - cost, 2),
        "positive_expected_net_value": bool(uplift * margin - cost > 0),
        "model_version": bundle.get("model_version", "unknown"),
        "data_classification": "synthetic_portfolio_model; validate before real-world use",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok" if _bundle is not None else "model_not_loaded",
        "model_loaded": _bundle is not None,
        "model_version": _bundle.get("model_version") if _bundle else None,
        "synthetic_data_only": True,
    }


@app.post("/score")
def score_driver(row: DriverFeatures) -> dict:
    return _score_one(row, _ensure_model())


@app.post("/score/batch")
def score_batch(request: BatchScoreRequest) -> dict:
    bundle = _ensure_model()
    return {
        "count": len(request.drivers),
        "scores": [_score_one(row, bundle) for row in request.drivers],
        "note": "Predictions are not causal guarantees and should not trigger production incentives without prospective randomized validation.",
    }
