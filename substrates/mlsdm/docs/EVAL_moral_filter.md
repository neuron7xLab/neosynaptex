# Moral Filter Evaluation Suite

**Document Version:** 1.0.0
**Last Updated:** December 2025
**Status:** Active

---

## Overview

This evaluation suite verifies the behavioral correctness and invariant properties of `MoralFilterV2`, the adaptive moral threshold filter that governs LLM output acceptance in MLSDM.

### What This Eval Measures

1. **Threshold Bounds (INV-MF-1)**: Threshold is always within [0.30, 0.90]
2. **Adaptation Bounds (INV-MF-2)**: Single adaptation step changes threshold by ≤0.05
3. **EMA Stability (INV-MF-3)**: EMA accept rate is always within [0.0, 1.0]
4. **Evaluation Behavior**: Correct accept/reject decisions based on moral values
5. **Drift Resistance**: Stability under adversarial or sustained inputs
6. **Edge Cases**: Correct handling of boundary values

### Component Under Test

```python
from mlsdm.cognition.moral_filter_v2 import MoralFilterV2
```

See [MORAL_FILTER_SPEC.md](../MORAL_FILTER_SPEC.md) for detailed specification.

---

## File Structure

```
evals/
├── __init__.py
├── moral_filter_scenarios.yaml    # Scenario definitions (25+ scenarios)
├── moral_filter_runner.py         # Evaluation execution engine
└── moral_filter_report.json       # Generated after run (not committed)

docs/
└── EVAL_moral_filter.md           # This documentation
```

---

## Scenarios File Structure

The scenarios are defined in `evals/moral_filter_scenarios.yaml`:

```yaml
- id: "SCENARIO_ID"
  description: "Human-readable description"
  input:
    initial_threshold: 0.50          # Optional initial threshold
    moral_values: [0.95, 0.05, ...]  # Sequence of moral values to evaluate
    iterations: 100                   # Optional: repeat values N times
  expected:
    properties:
      - "threshold >= 0.30"          # Properties that must hold
      - "last_decision == true"
    labels:
      test_type: "threshold_bounds"  # Categorical labels for grouping
```

### Scenario Types

| Type | ID Prefix | Description |
|------|-----------|-------------|
| Threshold Bounds | `TH_BOUNDS_*` | Verify threshold stays in [0.30, 0.90] |
| Evaluation | `EVAL_*` | Test accept/reject decisions |
| Adaptation | `ADAPT_*` | Test threshold adaptation logic |
| Drift Resistance | `DRIFT_*` | Test stability under sustained inputs |
| Edge Cases | `EDGE_*` | Test boundary conditions |
| EMA Stability | `EMA_*` | Test EMA bounds and convergence |

---

## Running the Evaluation

### Quick Start

```bash
# Run the full evaluation suite
python evals/moral_filter_runner.py

# Or via Makefile
make eval-moral_filter

# Run as module
python -m evals.moral_filter_runner
```

---

## Understanding the Results

### Console Output

Running the eval produces a human-readable report:

```
======================================================================
Moral Filter Evaluation Report
======================================================================
Scenarios file: /path/to/evals/moral_filter_scenarios.yaml
----------------------------------------------------------------------
SUMMARY
----------------------------------------------------------------------
  Total scenarios:  25
  Passed:           25
  Failed:           0
  Pass rate:        100.0%

----------------------------------------------------------------------
RESULTS BY TEST TYPE
----------------------------------------------------------------------
  test_type=adaptation_behavior: 4/4 (100%)
  test_type=drift_resistance: 4/4 (100%)
  test_type=edge_case: 5/5 (100%)
  test_type=ema_stability: 4/4 (100%)
  test_type=evaluation_behavior: 6/6 (100%)
  test_type=threshold_bounds: 5/5 (100%)

======================================================================
```

### JSON Report

A detailed JSON report is saved to `evals/moral_filter_report.json`:

```json
{
  "summary": {
    "total": 25,
    "passed": 25,
    "failed": 0,
    "pass_rate": 100.0
  },
  "by_property": {
    "threshold >= 0.30": {"passed": 8, "failed": 0},
    "threshold <= 0.90": {"passed": 8, "failed": 0},
    ...
  },
  "by_label": {
    "test_type=threshold_bounds": {"passed": 5, "failed": 0},
    ...
  },
  "per_scenario": [
    {
      "scenario_id": "TH_BOUNDS_001",
      "description": "Initial threshold should be within valid range",
      "passed": true,
      "properties_results": {
        "threshold >= 0.30": true,
        "threshold <= 0.90": true
      },
      "actual_values": {
        "threshold": 0.5,
        "initial_threshold": 0.5,
        "ema": 0.5
      },
      "error": null
    },
    ...
  ]
}
```

---

## Adding New Scenarios

### Step 1: Add to YAML

Edit `evals/moral_filter_scenarios.yaml`:

```yaml
- id: "MY_NEW_001"
  description: "Describe what this scenario tests"
  input:
    initial_threshold: 0.50
    moral_values: [0.75, 0.75, 0.75]
  expected:
    properties:
      - "threshold > initial_threshold"  # Expected behavior
    labels:
      test_type: "my_new_type"
      category: "custom"
```

### Step 2: Run to Verify

```bash
python evals/moral_filter_runner.py
```

### Supported Property Expressions

| Expression | Description |
|------------|-------------|
| `threshold >= X` | Threshold is at least X |
| `threshold <= X` | Threshold is at most X |
| `threshold > initial_threshold` | Threshold increased |
| `threshold < initial_threshold` | Threshold decreased |
| `threshold == initial_threshold` | Threshold unchanged |
| `last_decision == true` | Last evaluation accepted |
| `last_decision == false` | Last evaluation rejected |
| `delta_threshold <= X` | Max single-step change ≤ X |
| `ema >= X` | EMA is at least X |
| `ema <= X` | EMA is at most X |
| `abs(threshold - initial_threshold) < X` | Drift limited to X |

### Special Input Values

- `moral_values: "random_uniform_0_1"` - Generates random values in [0, 1]
- `iterations: N` - Repeats the moral_values sequence N times

---

## Metrics Reference

### Pass Rate

The primary metric is the **pass rate** - the percentage of scenarios where all properties hold:

```
pass_rate = (passed / total) * 100
```

A 100% pass rate indicates the MoralFilterV2 implementation satisfies all specified invariants.

### By-Property Breakdown

Shows which specific invariants passed/failed:

- `threshold >= 0.30` - INV-MF-1 lower bound
- `threshold <= 0.90` - INV-MF-1 upper bound
- `delta_threshold <= 0.05` - INV-MF-2 adaptation bound
- `ema >= 0.0`, `ema <= 1.0` - INV-MF-3 EMA bounds

### By-Label Breakdown

Groups results by test category:

- `test_type=threshold_bounds` - Invariant boundary tests
- `test_type=evaluation_behavior` - Decision logic tests
- `test_type=adaptation_behavior` - Threshold adaptation tests
- `test_type=drift_resistance` - Adversarial input tests
- `test_type=edge_case` - Boundary condition tests
- `test_type=ema_stability` - EMA convergence tests

---

## Integration with CI

The evaluation can be integrated into CI pipelines:

```yaml
# Example GitHub Actions step
- name: Run Moral Filter Evaluation
  run: |
    python -m evals.moral_filter_runner
```

---

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'evals'`:

```bash
# Run from repository root with PYTHONPATH
PYTHONPATH=. python evals/moral_filter_runner.py

# Or install the package in development mode
pip install -e .
```

### Failed Scenarios

If scenarios fail, check:

1. **Actual values** in the error output
2. **Property expressions** for typos
3. **MoralFilterV2 implementation** for regressions

Example failure output:

```
FAILED SCENARIOS
----------------------------------------------------------------------
  [TH_BOUNDS_002] Threshold remains bounded after sustained accepts
    FAILED: threshold <= 0.90
      Actual: {'threshold': 0.95, 'initial_threshold': 0.5, ...}
```

---

## References

- [MORAL_FILTER_SPEC.md](../MORAL_FILTER_SPEC.md) - Detailed specification
- [tests/property/test_moral_filter_properties.py](../tests/property/test_moral_filter_properties.py) - Property-based tests
- [tests/validation/test_moral_filter_effectiveness.py](../tests/validation/test_moral_filter_effectiveness.py) - Effectiveness validation

---

**Document Status:** Active
**Review Cycle:** Per major eval update
**Last Reviewed:** December 2025
