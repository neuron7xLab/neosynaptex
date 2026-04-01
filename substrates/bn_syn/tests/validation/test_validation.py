import pytest
from pydantic import ValidationError

from bnsyn.validation import NetworkValidationConfig


@pytest.mark.validation
def test_invalid_dt_ms() -> None:
    with pytest.raises(ValidationError):
        NetworkValidationConfig(dt_ms=2.0)


@pytest.mark.validation
def test_invalid_fraction_inhibitory() -> None:
    with pytest.raises(ValidationError):
        NetworkValidationConfig(frac_inhib=1.5)


@pytest.mark.validation
def test_valid_config_defaults() -> None:
    config = NetworkValidationConfig()
    assert config.N == 200
