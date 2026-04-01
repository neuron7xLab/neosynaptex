from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net.integration.runtime_config import assemble_validation_config
from mycelium_fractal_net.integration.schemas import ValidateRequest


def test_assemble_validation_config_applies_profile_and_env(monkeypatch) -> None:
    monkeypatch.setenv("MFN_CONFIG_PROFILE", "dev")
    monkeypatch.setenv("MFN_CONFIG_OVERRIDES", "validation.seed=100,validation.batch_size=6")
    cfg = assemble_validation_config()

    assert cfg.seed == 100  # env overrides profile/defaults
    assert cfg.batch_size == 6
    assert cfg.grid_size == 32  # from dev profile


def test_assemble_validation_config_allows_request_override(monkeypatch) -> None:
    monkeypatch.setenv("MFN_CONFIG_PROFILE", "dev")
    monkeypatch.setenv("MFN_CONFIG_OVERRIDES", "validation.seed=100,validation.batch_size=6")

    request = ValidateRequest(seed=7, epochs=3, batch_size=5, grid_size=64, steps=64)
    cfg = assemble_validation_config(request)

    assert cfg.seed == 7  # request overrides env/profile
    assert cfg.batch_size == 5
    assert cfg.epochs == 3
    assert cfg.grid_size == 64
