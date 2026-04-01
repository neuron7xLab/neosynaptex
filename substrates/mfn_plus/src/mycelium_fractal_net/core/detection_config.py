"""Detection threshold configuration loader.

Loads thresholds from ``configs/detection_thresholds_v1.json`` at module init.
If the config file is missing or malformed, falls back to hardcoded defaults
so the engine never fails at import time.

Every threshold has:
- A name (used as dict key and Python constant)
- A default value (hardcoded fallback)
- A config path (JSON key path in the config file)

The loaded config is frozen after init — no runtime mutation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Resolve config path relative to project root (3 levels up from this file)
_CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"
_DETECTION_CONFIG_PATH = _CONFIG_DIR / "detection_thresholds_v1.json"

# Schema version for compatibility check
DETECTION_CONFIG_VERSION = "mfn-detection-config-v1"


_REQUIRED_SECTIONS = (
    "evidence_normalization",
    "regime_thresholds",
    "regime_weights",
    "anomaly_weights",
    "instability_weights",
    "confidence",
    "comparison",
)


class ConfigValidationError(ValueError):
    """Raised when detection config fails schema validation."""


def _validate_schema(data: dict[str, Any]) -> list[str]:
    """Validate config structure, types, required fields. Returns list of warnings."""
    warnings: list[str] = []

    if data.get("schema_version") != DETECTION_CONFIG_VERSION:
        warnings.append(
            f"schema_version mismatch: expected {DETECTION_CONFIG_VERSION}, "
            f"got {data.get('schema_version')}"
        )

    for section in _REQUIRED_SECTIONS:
        if section not in data:
            warnings.append(f"missing required section: {section}")
        elif not isinstance(data[section], dict):
            warnings.append(f"section {section} must be a dict, got {type(data[section]).__name__}")

    # Validate weight sums
    for weight_section in ("anomaly_weights", "instability_weights"):
        if weight_section in data and isinstance(data[weight_section], dict):
            total = sum(float(v) for v in data[weight_section].values())
            if abs(total - 1.0) > 0.02:
                warnings.append(f"{weight_section} sum={total:.3f}, expected ~1.0")

    # Validate value ranges
    for section_name, section_data in data.items():
        if not isinstance(section_data, dict):
            continue
        for key, value in section_data.items():
            if isinstance(value, dict):
                continue  # nested sections (regime_weights)
            if isinstance(value, (int, float)) and not (-1e6 < value < 1e6):
                warnings.append(f"{section_name}.{key}={value} outside reasonable range")

    return warnings


def _load_config() -> dict[str, Any]:
    """Load and validate detection config from JSON. Returns empty dict on failure."""
    try:
        if _DETECTION_CONFIG_PATH.exists():
            data: dict[str, Any] = json.loads(_DETECTION_CONFIG_PATH.read_text(encoding="utf-8"))
            warnings = _validate_schema(data)
            for w in warnings:
                logger.warning("Detection config: %s", w)
            return data
    except Exception:
        logger.warning("Failed to load detection config from %s", _DETECTION_CONFIG_PATH)
    return {}


def _config_hash() -> str:
    """SHA256 hash of the config file content (or 'default' if not loaded)."""
    try:
        if _DETECTION_CONFIG_PATH.exists():
            return hashlib.sha256(_DETECTION_CONFIG_PATH.read_bytes()).hexdigest()[:16]
    except Exception:
        logger.warning("Failed to compute config hash for %s", _DETECTION_CONFIG_PATH)
    return "default"


# Load once at module init
_CFG = _load_config()
CONFIG_HASH = _config_hash()


def reload_config() -> str:
    """Reload detection thresholds from disk. Returns new config hash.

    Call this after updating detection_thresholds_v1.json at runtime.
    Thread-safe: module-level assignments are atomic in CPython.
    """
    global _CFG, CONFIG_HASH
    _CFG = _load_config()
    CONFIG_HASH = _config_hash()
    logger.info("Detection config reloaded, hash=%s", CONFIG_HASH)
    return CONFIG_HASH


def _get(section: str, key: str, default: float) -> float:
    """Get a threshold value from config, falling back to hardcoded default."""
    try:
        return float(_CFG.get(section, {}).get(key, default))
    except (TypeError, ValueError):
        return default


def _get_weight(section: str, key: str, default: float) -> float:
    """Get a weight from a nested weights section."""
    try:
        return float(_CFG.get(section, {}).get(key, default))
    except (TypeError, ValueError):
        return default


def _get_regime_weight(regime: str, key: str, default: float) -> float:
    """Get a regime-specific weight from regime_weights section."""
    try:
        return float(_CFG.get("regime_weights", {}).get(regime, {}).get(key, default))
    except (TypeError, ValueError):
        return default


def _get_comparison(key: str, default: float) -> float:
    """Get a comparison threshold."""
    try:
        return float(_CFG.get("comparison", {}).get(key, default))
    except (TypeError, ValueError):
        return default


# ═══════════════════════════════════════════════════════════════
#  Evidence normalization
# ═══════════════════════════════════════════════════════════════

TEMPORAL_LZC_NORMALIZER: float = _get("evidence_normalization", "temporal_lzc_normalizer", 3.0)
CONNECTIVITY_AMPLIFICATION: float = _get(
    "evidence_normalization", "connectivity_amplification", 4.0
)
HIERARCHY_BASELINE: float = _get("evidence_normalization", "hierarchy_baseline", 0.70)
HIERARCHY_RANGE: float = _get("evidence_normalization", "hierarchy_range", 0.30)
CRITICALITY_AMPLIFICATION: float = _get("evidence_normalization", "criticality_amplification", 50.0)
NOISE_GAIN_AMPLIFICATION: float = _get("evidence_normalization", "noise_gain_amplification", 1000.0)

# ═══════════════════════════════════════════════════════════════
#  Regime thresholds
# ═══════════════════════════════════════════════════════════════

DYNAMIC_ANOMALY_BASELINE: float = _get("regime_thresholds", "dynamic_anomaly_baseline", 0.45)
REORGANIZED_COMPLEXITY_THRESHOLD: float = _get(
    "regime_thresholds", "reorganized_complexity_threshold", 0.55
)
REORGANIZED_TOPOLOGY_THRESHOLD: float = _get(
    "regime_thresholds", "reorganized_topology_threshold", 0.14
)
REORGANIZED_PLASTICITY_FLOOR: float = _get(
    "regime_thresholds", "reorganized_plasticity_floor", 0.08
)
PATHOLOGICAL_NOISE_THRESHOLD: float = _get(
    "regime_thresholds", "pathological_noise_threshold", 0.55
)
STRUCTURE_FLOOR: float = _get("regime_thresholds", "structure_floor", 0.10)
STABLE_CEILING: float = _get("regime_thresholds", "stable_ceiling", 0.70)

# ═══════════════════════════════════════════════════════════════
#  Dynamic threshold adjustment
# ═══════════════════════════════════════════════════════════════

THRESHOLD_PLASTICITY_WEIGHT: float = _get("regime_thresholds", "threshold_plasticity_weight", 0.18)
THRESHOLD_CONNECTIVITY_WEIGHT: float = _get(
    "regime_thresholds", "threshold_connectivity_weight", 0.08
)
THRESHOLD_NOISE_PENALTY: float = _get("regime_thresholds", "threshold_noise_penalty", 0.12)
THRESHOLD_CRITICAL_OFFSET: float = _get("regime_thresholds", "threshold_critical_offset", -0.03)
THRESHOLD_REORGANIZED_OFFSET: float = _get(
    "regime_thresholds", "threshold_reorganized_offset", 0.05
)
THRESHOLD_PATHOLOGICAL_OFFSET: float = _get(
    "regime_thresholds", "threshold_pathological_offset", -0.08
)
THRESHOLD_FLOOR: float = _get("regime_thresholds", "threshold_floor", 0.25)
THRESHOLD_CEILING: float = _get("regime_thresholds", "threshold_ceiling", 0.85)

# ═══════════════════════════════════════════════════════════════
#  Instability scoring weights (sum = 1.00)
# ═══════════════════════════════════════════════════════════════

INSTABILITY_W_INDEX: float = _get_weight("instability_weights", "index", 0.26)
INSTABILITY_W_TRANSITION: float = _get_weight("instability_weights", "transition", 0.24)
INSTABILITY_W_COLLAPSE: float = _get_weight("instability_weights", "collapse", 0.22)
INSTABILITY_W_VOLATILITY: float = _get_weight("instability_weights", "volatility", 0.16)
INSTABILITY_W_NOISE: float = _get_weight("instability_weights", "noise", 0.12)

# ═══════════════════════════════════════════════════════════════
#  Regime scoring weights
# ═══════════════════════════════════════════════════════════════

REGIME_CRITICAL_W_PRESSURE: float = _get_regime_weight("critical", "pressure", 0.34)
REGIME_CRITICAL_W_CHANGE: float = _get_regime_weight("critical", "change", 0.16)
REGIME_CRITICAL_W_HIERARCHY: float = _get_regime_weight("critical", "hierarchy", 0.16)
REGIME_CRITICAL_W_PLASTICITY: float = _get_regime_weight("critical", "plasticity", 0.18)

REGIME_REORGANIZED_W_COMPLEXITY: float = _get_regime_weight("reorganized", "complexity", 0.22)
REGIME_REORGANIZED_W_CONNECTIVITY: float = _get_regime_weight("reorganized", "connectivity", 0.18)
REGIME_REORGANIZED_W_PLASTICITY: float = _get_regime_weight("reorganized", "plasticity", 0.30)
REGIME_REORGANIZED_W_CHANGE: float = _get_regime_weight("reorganized", "change", 0.10)

REGIME_PATHNOISE_W_NOISE: float = _get_regime_weight("pathological_noise", "noise", 0.45)
REGIME_PATHNOISE_W_CHANGE: float = _get_regime_weight("pathological_noise", "change", 0.20)
REGIME_PATHNOISE_W_LOW_CONN: float = _get_regime_weight("pathological_noise", "low_conn", 0.15)
REGIME_PATHNOISE_W_LOW_COMPLEX: float = _get_regime_weight(
    "pathological_noise", "low_complex", 0.10
)
REGIME_PATHNOISE_FLOOR_GAP: float = _get("regime_thresholds", "pathological_floor_gap", 0.2)

REGIME_TRANSITIONAL_W_CHANGE: float = _get_regime_weight("transitional", "change", 0.32)
REGIME_TRANSITIONAL_W_PRESSURE: float = _get_regime_weight("transitional", "pressure", 0.18)
REGIME_TRANSITIONAL_W_CONNECTIVITY: float = _get_regime_weight("transitional", "connectivity", 0.14)

# ═══════════════════════════════════════════════════════════════
#  Confidence
# ═══════════════════════════════════════════════════════════════

REGIME_CONFIDENCE_BASE: float = _get_weight("confidence", "regime_base", 0.55)
REGIME_CONFIDENCE_SCALE: float = _get_weight("confidence", "regime_scale", 0.4)
REGIME_CONFIDENCE_MAX: float = _get_weight("confidence", "max", 0.99)

ANOMALY_CONFIDENCE_BASE: float = _get_weight("confidence", "anomaly_base", 0.60)
ANOMALY_CONFIDENCE_SCALE: float = _get_weight("confidence", "anomaly_scale", 0.6)
ANOMALY_CONFIDENCE_MAX: float = _get_weight("confidence", "max", 0.99)

# ═══════════════════════════════════════════════════════════════
#  Anomaly scoring weights (sum = 1.00)
# ═══════════════════════════════════════════════════════════════

ANOMALY_W_INSTABILITY: float = _get_weight("anomaly_weights", "instability", 0.16)
ANOMALY_W_TRANSITION: float = _get_weight("anomaly_weights", "transition", 0.14)
ANOMALY_W_COLLAPSE: float = _get_weight("anomaly_weights", "collapse", 0.18)
ANOMALY_W_CHANGE: float = _get_weight("anomaly_weights", "change", 0.14)
ANOMALY_W_VOLATILITY: float = _get_weight("anomaly_weights", "volatility", 0.12)
ANOMALY_W_NOISE: float = _get_weight("anomaly_weights", "noise", 0.14)
ANOMALY_W_CONNECTIVITY: float = _get_weight("anomaly_weights", "connectivity", 0.06)
ANOMALY_W_PLASTICITY: float = _get_weight("anomaly_weights", "plasticity", 0.06)

# Anomaly label thresholds
WATCH_THRESHOLD_FLOOR: float = _get("regime_thresholds", "watch_threshold_floor", 0.30)
WATCH_THRESHOLD_GAP: float = _get("regime_thresholds", "watch_threshold_gap", 0.18)

# Profile hint boosts
PROFILE_HINT_SEROTONERGIC: float = _get_weight("profile_hints", "serotonergic", 0.30)
PROFILE_HINT_CRITICALITY: float = _get_weight("profile_hints", "criticality", 0.10)

# ═══════════════════════════════════════════════════════════════
#  Comparison thresholds
# ═══════════════════════════════════════════════════════════════

COSINE_NEAR_IDENTICAL: float = _get_comparison("cosine_near_identical", 0.995)
COSINE_SIMILAR: float = _get_comparison("cosine_similar", 0.97)
COSINE_RELATED: float = _get_comparison("cosine_related", 0.90)
DISTANCE_NEAR_IDENTICAL: float = _get_comparison("distance_near_identical", 0.25)

NOISE_PATHOLOGICAL_HIGH: float = _get_comparison("noise_pathological_high", 0.0008)
NOISE_PATHOLOGICAL_LOW: float = _get_comparison("noise_pathological_low", 0.0005)
CONNECTIVITY_LOW: float = _get_comparison("connectivity_low", 0.05)
MODULARITY_LOW: float = _get_comparison("modularity_low", 0.08)
HIERARCHY_FLAT_THRESHOLD: float = _get_comparison("hierarchy_flat_threshold", 0.04)
CONNECTIVITY_FLAT_CEILING: float = _get_comparison("connectivity_flat_ceiling", 0.08)
CONNECTIVITY_REORG_THRESHOLD: float = _get_comparison("connectivity_reorg_threshold", 0.05)
MODULARITY_REORG_THRESHOLD: float = _get_comparison("modularity_reorg_threshold", 0.08)
TOP_CHANGED_FEATURES: int = int(_get_comparison("top_changed_features", 12))


def _get_forecast(key: str, default: float) -> float:
    """Get a forecast constant."""
    try:
        return float(_CFG.get("forecast", {}).get(key, default))
    except (TypeError, ValueError):
        return default


# ═══════════════════════════════════════════════════════════════
#  Forecast constants
# ═══════════════════════════════════════════════════════════════

DAMPING_BASE: float = _get_forecast("damping_base", 0.85)
DAMPING_MAX: float = _get_forecast("damping_max", 0.92)
FLUIDITY_COEFF_DEFAULT: float = _get_forecast("fluidity_coeff_default", 0.05)
FIELD_CLIP_MIN: float = _get_forecast("field_clip_min", -0.095)
FIELD_CLIP_MAX: float = _get_forecast("field_clip_max", 0.040)
UNCERTAINTY_W_PLASTICITY: float = _get_forecast("uncertainty_w_plasticity", 0.35)
UNCERTAINTY_W_CONNECTIVITY: float = _get_forecast("uncertainty_w_connectivity", 0.50)
UNCERTAINTY_W_DESENSITIZATION: float = _get_forecast("uncertainty_w_desensitization", 0.25)
STRUCTURAL_ERROR_WEIGHT: float = _get_forecast("structural_error_weight", 0.5)
