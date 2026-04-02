"""8 tests for ConfigRegistry — schema validation + NFI invariant enforcement."""

import pytest

from core.config_registry import ConfigRegistry


@pytest.fixture()
def registry():
    reg = ConfigRegistry()
    reg.register_schema(
        "bn_syn",
        {
            "n_neurons": {"type": "int", "required": True, "min": 1, "max": 100000},
            "sigma_target": {"type": "float", "required": True, "min": 0.0, "max": 2.0},
            "window": {"type": "int", "required": False, "min": 8, "max": 256},
        },
        defaults={"n_neurons": 1000, "sigma_target": 0.98, "window": 16},
    )
    return reg


def test_valid_config(registry):
    result = registry.validate("bn_syn", {"n_neurons": 500, "sigma_target": 0.98})
    assert result.valid
    assert len(result.errors) == 0


def test_missing_required_field(registry):
    result = registry.validate("bn_syn", {"sigma_target": 0.98})
    assert not result.valid
    assert any("n_neurons" in e and "required" in e for e in result.errors)


def test_out_of_range(registry):
    result = registry.validate("bn_syn", {"n_neurons": -1, "sigma_target": 0.98})
    assert not result.valid
    assert any("min" in e for e in result.errors)


def test_invariant_gamma_in_config():
    reg = ConfigRegistry()
    errors = reg.invariant_check({"gamma": 1.0})
    assert any("INV-1" in e for e in errors)


def test_invariant_modulation_bound():
    reg = ConfigRegistry()
    errors = reg.invariant_check({"modulation_bound": 0.1})
    assert any("INV-3" in e for e in errors)


def test_invariant_ssi_mode():
    reg = ConfigRegistry()
    errors = reg.invariant_check({"ssi_mode": "internal"})
    assert any("INV-SSI" in e for e in errors)


def test_merge_valid(registry):
    base = registry.get_defaults("bn_syn")
    result = registry.merge(base, {"n_neurons": 2000})
    assert result["n_neurons"] == 2000
    assert result["sigma_target"] == 0.98


def test_merge_invariant_violation(registry):
    base = registry.get_defaults("bn_syn")
    with pytest.raises(ValueError, match="invariants"):
        registry.merge(base, {"gamma": 1.0})
