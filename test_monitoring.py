import pandas as pd
from src.monitoring import _psi


def test_psi_is_low_for_same_distribution():
    reference = pd.Series(range(1000))
    current = pd.Series(range(1000))
    assert _psi(reference, current) == 0.0


def test_psi_is_defined_for_shifted_distribution():
    reference = pd.Series(range(1000))
    current = pd.Series(range(500, 1500))
    value = _psi(reference, current)
    assert value is not None
    assert value > 0.1
