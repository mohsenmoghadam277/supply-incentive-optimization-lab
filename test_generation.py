import pandas as pd
from src.generate_data import generate_datasets


def test_generated_data_is_reproducible_and_candidate_has_no_outcomes(tmp_path):
    exp1, cand1 = generate_datasets(tmp_path / "run_a", seed=7)
    exp2, cand2 = generate_datasets(tmp_path / "run_b", seed=7)
    assert len(exp1) == 12_000
    assert int(exp1.treatment.sum()) == 5_899
    assert int((exp1.treatment == 0).sum()) == 6_101
    pd.testing.assert_frame_equal(exp1, exp2)
    pd.testing.assert_frame_equal(cand1, cand2)
    assert len(cand1) == 3_000
    assert "trips_next_week" not in cand1.columns
    assert "treatment" not in cand1.columns
    assert set(exp1.synthetic_data.unique()) == {1}
