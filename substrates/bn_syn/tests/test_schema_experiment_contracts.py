"""Contract tests for experiment schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bnsyn.schemas.experiment import BNSynExperimentConfig


def test_experiment_config_rejects_invalid_dt() -> None:
    with pytest.raises(ValidationError, match=r"dt_ms must be one of"):
        BNSynExperimentConfig(
            experiment={"name": "quickstart", "version": "v1", "seeds": [1]},
            network={"size": 10},
            simulation={"duration_ms": 1.0, "dt_ms": 0.2},
        )


def test_experiment_config_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError, match=r"Extra inputs are not permitted"):
        BNSynExperimentConfig(
            experiment={"name": "quickstart", "version": "v1", "seeds": [1], "extra": 1},
            network={"size": 10},
            simulation={"duration_ms": 1.0, "dt_ms": 0.1},
        )


def test_experiment_config_requires_seed_list() -> None:
    with pytest.raises(ValidationError, match=r"at least 1 item"):
        BNSynExperimentConfig(
            experiment={"name": "quickstart", "version": "v1", "seeds": []},
            network={"size": 10},
            simulation={"duration_ms": 1.0, "dt_ms": 0.1},
        )


def test_experiment_config_requires_name_pattern() -> None:
    with pytest.raises(ValidationError, match=r"String should match pattern"):
        BNSynExperimentConfig(
            experiment={"name": "Bad Name", "version": "v1", "seeds": [1]},
            network={"size": 10},
            simulation={"duration_ms": 1.0, "dt_ms": 0.1},
        )


def test_experiment_config_rejects_duration_not_multiple_of_dt() -> None:
    with pytest.raises(ValidationError, match=r"duration_ms must be an integer multiple"):
        BNSynExperimentConfig(
            experiment={"name": "quickstart", "version": "v1", "seeds": [1]},
            network={"size": 10},
            simulation={"duration_ms": 1.25, "dt_ms": 0.1},
        )


def test_experiment_config_rejects_non_finite_external_current() -> None:
    with pytest.raises(ValidationError, match=r"external_current_pA must be a finite real number"):
        BNSynExperimentConfig(
            experiment={"name": "quickstart", "version": "v1", "seeds": [1]},
            network={"size": 10},
            simulation={"duration_ms": 1.0, "dt_ms": 0.1, "external_current_pA": float("inf")},
        )


def test_experiment_config_defaults_include_artifact_fields() -> None:
    config = BNSynExperimentConfig(
        experiment={"name": "quickstart", "version": "v1", "seeds": [1]},
        network={"size": 10},
        simulation={"duration_ms": 1.0, "dt_ms": 0.1},
    )
    assert config.simulation.external_current_pA == 0.0
    assert config.simulation.artifact_dir is None
