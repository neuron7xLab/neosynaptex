# Detection Threshold Provenance

**Config:** `configs/detection_thresholds_v1.json`
**Calibration date:** 2026-03-17
**Calibration scenarios:** 6 canonical profiles

## Fragile Thresholds (from KNOWN_LIMITATIONS.md)

### 1. DYNAMIC_ANOMALY_BASELINE = 0.45

**Purpose:** Separates "nominal" from "watch" anomaly regime.
**Fragility:** Moderate — label flips near boundary.
**Calibration method:** Median anomaly score across 6 canonical scenarios.
**Sensitivity:** ±10% changes classification for 2/6 scenarios.
**Source:** Empirical calibration against known-good simulations.

### 2. PATHOLOGICAL_NOISE_THRESHOLD = 0.55

**Purpose:** Detects pathological noise regime (observation noise artifacts).
**Fragility:** HIGH — regime-sensitive.
**Calibration method:** 95th percentile of noise evidence across observation_noise scenarios.
**Sensitivity:** ±5% can misclassify noise-free runs as noisy.
**Source:** Sensitivity sweep (`scripts/sensitivity_sweep.py`).

### 3. REORGANIZED_COMPLEXITY_THRESHOLD = 0.55

**Purpose:** Detects serotonergic reorganization regime.
**Fragility:** Moderate — sensitive to plasticity index range.
**Calibration method:** Mean complexity score during serotonergic scenario.
**Sensitivity:** ±10% changes regime label for serotonergic profile.
**Source:** Serotonergic scenario calibration.

## Update Protocol

1. Run `scripts/sensitivity_sweep.py` to measure current sensitivity
2. If threshold change needed, run against ALL 6 calibration scenarios
3. Document before/after in commit message
4. Golden hashes may change — follow GOLDEN_ARTIFACT_POLICY.md

## Confidence Assessment

| Threshold | Value | Sensitivity | Confidence |
|-----------|-------|-------------|------------|
| dynamic_anomaly_baseline | 0.45 | ±10% flips 2/6 | Medium |
| pathological_noise_threshold | 0.55 | ±5% flips 1/6 | Low |
| reorganized_complexity_threshold | 0.55 | ±10% flips 1/6 | Medium |
| stable_ceiling | 0.70 | ±20% safe | High |
| structure_floor | 0.10 | ±20% safe | High |

**TODO:** Bootstrap confidence intervals for the 3 fragile thresholds
(requires running 1000+ perturbation samples per threshold).
