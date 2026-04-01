from __future__ import annotations

import json
from pathlib import Path

import pytest

from mycelium_fractal_net.config_profiles import (
    ConfigProfile,
    ConfigValidationError,
    apply_overrides,
    load_config_profile,
)


def test_load_and_validate_builtin_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MFN_CONFIG_OVERRIDES", raising=False)
    profile = load_config_profile("small")
    assert isinstance(profile, ConfigProfile)
    assert profile.validation.grid_size == 32
    assert profile.federated.byzantine_fraction == pytest.approx(0.2)


def test_environment_override_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    overrides = "validation.steps=64,simulation.turing_enabled=false"
    monkeypatch.setenv("MFN_CONFIG_OVERRIDES", overrides)
    profile = load_config_profile("small")
    assert profile.validation.steps == 64
    assert profile.simulation.turing_enabled is False


def test_invalid_profile_rejected(tmp_path: Path) -> None:
    bad_payload = json.loads(Path("configs/small.json").read_text())
    bad_payload["validation"]["grid_size"] = 1  # below GRID_SIZE_MIN
    bad_payload["name"] = "invalid"
    bad_path = tmp_path / "invalid.json"
    bad_path.write_text(json.dumps(bad_payload))

    with pytest.raises(ConfigValidationError):
        load_config_profile("invalid", base_path=tmp_path)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ("validation.seed=99", 99),
        ("validation.device=gpu", "gpu"),
        ("simulation.turing_threshold=0.9", 0.9),
    ],
)
def test_apply_overrides_parses_values(overrides: str, expected: object) -> None:
    base = {
        "validation": {"seed": 1, "device": "cpu"},
        "simulation": {"turing_threshold": 0.75},
    }
    updated = apply_overrides(base, overrides)
    key_path, _ = overrides.split("=", 1)
    parent, leaf = key_path.split(".")
    assert updated[parent][leaf] == expected
