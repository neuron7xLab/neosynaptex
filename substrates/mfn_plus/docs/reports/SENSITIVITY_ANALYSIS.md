# Sensitivity Analysis — Detection Thresholds

Scenarios tested: 6

Thresholds analyzed: 10


| Threshold | Value | ±5% flips | ±10% flips | ±20% flips | Fragile? |
|-----------|-------|-----------|------------|------------|----------|
| DYNAMIC_ANOMALY_BASELINE | 0.450 | 0% | 0% | 0% | no |
| STABLE_CEILING | 0.700 | 0% | 0% | 0% | no |
| THRESHOLD_FLOOR | 0.250 | 0% | 0% | 0% | no |
| THRESHOLD_CEILING | 0.850 | 0% | 0% | 0% | no |
| WATCH_THRESHOLD_FLOOR | 0.300 | 0% | 0% | 0% | no |
| WATCH_THRESHOLD_GAP | 0.180 | 0% | 0% | 0% | no |
| PATHOLOGICAL_NOISE_THRESHOLD | 0.550 | 0% | 0% | 0% | no |
| REORGANIZED_COMPLEXITY_THRESHOLD | 0.550 | 0% | 0% | 0% | no |
| REORGANIZED_PLASTICITY_FLOOR | 0.080 | 0% | 0% | 0% | no |
| STRUCTURE_FLOOR | 0.100 | 0% | 0% | 0% | no |

**Fragile thresholds (>10% flip at ±5%): 0**

Fragile thresholds should be reviewed for robustness.
See `configs/detection_thresholds_v1.json` for current values.
