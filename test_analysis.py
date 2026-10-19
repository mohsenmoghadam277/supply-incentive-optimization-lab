import numpy as np
import pandas as pd
from src.analyze_experiment import _welch_result, analyze_experiment


def test_welch_result_has_positive_lift_and_ordered_ci():
    control = pd.Series([10, 11, 12, 11, 9, 10, 12, 11], dtype=float)
    treated = pd.Series([12, 13, 14, 13, 11, 12, 14, 13], dtype=float)
    result = _welch_result(treated, control)
    assert np.isclose(result["difference_treatment_minus_control"], 2.0)
    assert result["ci95_low"] < result["difference_treatment_minus_control"] < result["ci95_high"]
    assert result["p_value_welch"] < 0.05


def test_cost_is_descriptive_not_significance_test(tmp_path):
    df = pd.DataFrame({
        "treatment": [1, 1, 1, 1, 0, 0, 0, 0],
        "trips_next_week": [12, 13, 11, 12, 10, 10, 11, 9],
        "online_hours_next_week": [8, 9, 8, 10, 7, 7, 8, 7],
        "active_next_week": [1, 1, 0, 1, 1, 0, 1, 0],
        "incentive_cost_toman": [80, 90, 100, 90, 0, 0, 0, 0],
        "zone": ["central"] * 8,
        "daypart": ["morning"] * 8,
    })
    out = analyze_experiment(df, tmp_path, margin_per_trip=50)
    cost = out["summary"].loc[out["summary"].metric == "incentive_cost_toman"].iloc[0]
    assert pd.isna(cost["p_value_welch"])
    assert pd.isna(cost["ci95_low"])
    assert out["economics"]["data_classification"] == "synthetic_educational_data"
