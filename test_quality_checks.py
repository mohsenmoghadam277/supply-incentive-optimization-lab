import pytest
from src.generate_data import generate_datasets
from src.quality_checks import validate_datasets


def test_data_quality_passes_for_generated_synthetic_data(tmp_path):
    experiment, candidates = generate_datasets(tmp_path / "raw", seed=11)
    report = validate_datasets(experiment, candidates, tmp_path / "quality.json")
    assert report["status"] == "pass"
    assert report["checks"]["candidate_overlap_with_experiment_ids"] == 0
    assert report["checks"]["post_outcome_features_in_candidates"] == []


def test_data_quality_rejects_post_outcome_leakage_in_candidates(tmp_path):
    experiment, candidates = generate_datasets(tmp_path / "raw", seed=12)
    candidates["trips_next_week"] = 10
    with pytest.raises(ValueError, match="candidate leakage"):
        validate_datasets(experiment, candidates, tmp_path / "quality.json")
