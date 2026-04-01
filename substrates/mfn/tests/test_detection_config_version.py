"""Verify detection constants match versioned config file.

If this test fails, either:
1. Constants in detect.py were changed without updating the config JSON
2. Config JSON was updated without updating detect.py constants
Both require explicit version bump and re-calibration evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_detection_config_version_matches() -> None:
    from mycelium_fractal_net.core.detect import DETECTION_CONFIG_VERSION

    config_path = ROOT / "configs" / "detection_thresholds_v1.json"
    config = json.loads(config_path.read_text())
    assert config["schema_version"] == DETECTION_CONFIG_VERSION


def test_anomaly_weights_sum_to_one() -> None:
    config_path = ROOT / "configs" / "detection_thresholds_v1.json"
    config = json.loads(config_path.read_text())
    weights = config["anomaly_weights"]
    total = sum(weights.values())
    assert total == pytest.approx(1.0, abs=1e-10), f"Anomaly weights sum to {total}, not 1.0"


def test_instability_weights_sum_to_one() -> None:
    config_path = ROOT / "configs" / "detection_thresholds_v1.json"
    config = json.loads(config_path.read_text())
    weights = config["instability_weights"]
    total = sum(weights.values())
    assert total == pytest.approx(1.0, abs=1e-10), f"Instability weights sum to {total}, not 1.0"


def test_constants_match_config_json() -> None:
    """Verify detect.py constants match the versioned config file."""
    from mycelium_fractal_net.core import detect

    config_path = ROOT / "configs" / "detection_thresholds_v1.json"
    config = json.loads(config_path.read_text())

    # Evidence normalization
    norm = config["evidence_normalization"]
    assert norm["temporal_lzc_normalizer"] == detect._TEMPORAL_LZC_NORMALIZER
    assert norm["connectivity_amplification"] == detect._CONNECTIVITY_AMPLIFICATION
    assert norm["hierarchy_baseline"] == detect._HIERARCHY_BASELINE
    assert norm["hierarchy_range"] == detect._HIERARCHY_RANGE
    assert norm["criticality_amplification"] == detect._CRITICALITY_AMPLIFICATION
    assert norm["noise_gain_amplification"] == detect._NOISE_GAIN_AMPLIFICATION

    # Regime thresholds
    rt = config["regime_thresholds"]
    assert rt["dynamic_anomaly_baseline"] == detect._DYNAMIC_ANOMALY_BASELINE
    assert rt["reorganized_complexity_threshold"] == detect._REORGANIZED_COMPLEXITY_THRESHOLD
    assert rt["reorganized_topology_threshold"] == detect._REORGANIZED_TOPOLOGY_THRESHOLD
    assert rt["reorganized_plasticity_floor"] == detect._REORGANIZED_PLASTICITY_FLOOR
    assert rt["pathological_noise_threshold"] == detect._PATHOLOGICAL_NOISE_THRESHOLD
    assert rt["structure_floor"] == detect._STRUCTURE_FLOOR
    assert rt["stable_ceiling"] == detect._STABLE_CEILING

    # Anomaly weights
    aw = config["anomaly_weights"]
    assert aw["instability"] == detect._ANOMALY_W_INSTABILITY
    assert aw["transition"] == detect._ANOMALY_W_TRANSITION
    assert aw["collapse"] == detect._ANOMALY_W_COLLAPSE
    assert aw["change"] == detect._ANOMALY_W_CHANGE
    assert aw["volatility"] == detect._ANOMALY_W_VOLATILITY
    assert aw["noise"] == detect._ANOMALY_W_NOISE
    assert aw["connectivity"] == detect._ANOMALY_W_CONNECTIVITY
    assert aw["plasticity"] == detect._ANOMALY_W_PLASTICITY

    # Profile hints
    ph = config["profile_hints"]
    assert ph["serotonergic"] == detect._PROFILE_HINT_SEROTONERGIC
    assert ph["criticality"] == detect._PROFILE_HINT_CRITICALITY


def test_compare_constants_match_config() -> None:
    """Compare thresholds in code must match versioned config."""
    from mycelium_fractal_net.core import compare

    config_path = ROOT / "configs" / "detection_thresholds_v1.json"
    config = json.loads(config_path.read_text())
    cc = config["comparison"]

    assert cc["cosine_near_identical"] == compare._COSINE_NEAR_IDENTICAL
    assert cc["cosine_similar"] == compare._COSINE_SIMILAR
    assert cc["cosine_related"] == compare._COSINE_RELATED
    assert cc["distance_near_identical"] == compare._DISTANCE_NEAR_IDENTICAL
    assert cc["noise_pathological_high"] == compare._NOISE_PATHOLOGICAL_HIGH
    assert cc["noise_pathological_low"] == compare._NOISE_PATHOLOGICAL_LOW
    assert cc["connectivity_low"] == compare._CONNECTIVITY_LOW
    assert cc["modularity_low"] == compare._MODULARITY_LOW
    assert cc["hierarchy_flat_threshold"] == compare._HIERARCHY_FLAT_THRESHOLD
    assert cc["connectivity_flat_ceiling"] == compare._CONNECTIVITY_FLAT_CEILING
    assert cc["connectivity_reorg_threshold"] == compare._CONNECTIVITY_REORG_THRESHOLD
    assert cc["modularity_reorg_threshold"] == compare._MODULARITY_REORG_THRESHOLD
    assert cc["top_changed_features"] == compare._TOP_CHANGED_FEATURES
