"""Shared configuration for the synthetic supply-incentive portfolio project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "project_outputs"
ARTIFACT_DIR = ROOT / "artifacts"

SEED = 42
N_EXPERIMENT_DRIVERS = 12_000
N_CANDIDATES = 3_000
TREATMENT_N = 5_899
CONTROL_N = N_EXPERIMENT_DRIVERS - TREATMENT_N
TOP_K_FRACTION = 0.20
ASSUMED_GROSS_MARGIN_TOMAN = 50_000
CAMPAIGN_ID = "INCENTIVE_SYNTH_001"

CATEGORICAL_FEATURES = ["zone", "daypart"]
NUMERIC_FEATURES = [
    "avg_online_hours_4w",
    "avg_trips_4w",
    "cancellation_rate",
    "demand_index",
    "acceptance_rate",
    "tenure_days",
    "is_active_pre",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
OUTCOME_TRIPS = "trips_next_week"
TREATMENT_COL = "treatment"
COST_COL = "incentive_cost_toman"

ZONE_VALUES = ["central", "east", "north", "south", "west"]
DAYPART_VALUES = ["morning", "afternoon", "evening", "late_night"]
