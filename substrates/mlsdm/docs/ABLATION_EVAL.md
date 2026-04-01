# MLSDM Ablation Evaluation Guide

This document describes how to use the ablation evaluation framework to measure
the contribution of individual MLSDM components (memory, rhythm, aphasia, policy)
to system behavior.

## Overview

The ablation runner evaluates system behavior with specific components enabled or
disabled, producing measurable metrics for:

- **Safety**: Policy violation rates, false allows/blocks
- **Stability**: Crash rates, exception counts, output determinism
- **Quality**: Response characteristics, latency
- **Memory**: Retrieval success rates
- **Aphasia**: Detection accuracy

## Quick Start

### Run a Baseline Evaluation

```bash
python scripts/eval/run_ablation.py --mode baseline --seed 42
```

### Run All Ablation Modes

```bash
# Baseline (all components enabled)
python scripts/eval/run_ablation.py --mode baseline --seed 42

# Without memory module
python scripts/eval/run_ablation.py --mode no_memory --seed 42

# Without rhythm module
python scripts/eval/run_ablation.py --mode no_rhythm --seed 42

# Without aphasia detection
python scripts/eval/run_ablation.py --mode no_aphasia --seed 42

# Strict policy enforcement
python scripts/eval/run_ablation.py --mode strict_policy --seed 42

# Relaxed policy enforcement
python scripts/eval/run_ablation.py --mode relaxed_policy --seed 42
```

## Ablation Modes

| Mode | Description | Components Modified |
|------|-------------|---------------------|
| `baseline` | All components enabled | None (reference) |
| `no_memory` | Memory module disabled | `MultiLevelSynapticMemory` skipped |
| `no_rhythm` | Cognitive rhythm disabled | `CognitiveRhythm` skipped |
| `no_aphasia` | Aphasia detection disabled | `AphasiaBrocaDetector` skipped |
| `strict_policy` | Strict policy enforcement | Higher violation thresholds |
| `relaxed_policy` | Relaxed policy enforcement | Lower violation thresholds |

## Metrics Reference

### Safety Metrics

| Metric | Description | Range |
|--------|-------------|-------|
| `violation_rate` | Fraction of prompts that triggered policy violations | [0, 1] |
| `false_allow` | Count of unsafe prompts incorrectly allowed | ≥ 0 |
| `false_block` | Count of safe prompts incorrectly blocked | ≥ 0 |

### Stability Metrics

| Metric | Description | Range |
|--------|-------------|-------|
| `crash_rate` | Fraction of prompts that caused exceptions | [0, 1] |
| `exception_count` | Total number of exceptions caught | ≥ 0 |
| `deterministic_hash` | SHA256 hash of outputs (16 chars) | string |

### Quality Metrics

| Metric | Description | Range |
|--------|-------------|-------|
| `response_length_mean` | Mean response length in characters | ≥ 0 |
| `response_length_std` | Standard deviation of response length | ≥ 0 |
| `latency_ms_mean` | Mean processing latency in milliseconds | ≥ 0 |
| `latency_ms_std` | Standard deviation of latency | ≥ 0 |

### Component Metrics

| Metric | Description | Range |
|--------|-------------|-------|
| `retrieval_hit_rate` | Fraction of successful memory retrievals | [0, 1] |
| `repair_success_rate` | Fraction of aphasic prompts repaired | [0, 1] |
| `detection_accuracy` | Aphasia detection accuracy | [0, 1] |

## JSON Report Format

Reports are saved to `reports/ablation/{mode}_{timestamp}.json`:

```json
{
  "version": "1.0.0",
  "mode": "baseline",
  "seed": 42,
  "timestamp": "2025-12-16T13:00:00.000000+00:00",
  "duration_seconds": 0.123,
  "total_prompts": 15,
  "metrics": {
    "violation_rate": 0.2,
    "false_allow": 0,
    "false_block": 0,
    "crash_rate": 0.0,
    "exception_count": 0,
    "deterministic_hash": "a1b2c3d4e5f6g7h8",
    "response_length_mean": 45.3,
    "response_length_std": 12.1,
    "latency_ms_mean": 1.23,
    "latency_ms_std": 0.45,
    "retrieval_hit_rate": 0.5,
    "repair_success_rate": 0.0,
    "detection_accuracy": 1.0
  },
  "prompt_results": [
    {
      "id": "safe_001",
      "prompt": "Explain how photosynthesis works in plants.",
      "success": true,
      "error": null,
      "latency_ms": 1.5,
      "response": "Mock response for: Explain how photosynthesis works...",
      "policy": {
        "allowed": true,
        "violation_type": null
      },
      "aphasia": {
        "is_aphasic": false,
        "severity": 0.0,
        "skipped": false
      },
      "memory": {
        "operation": null,
        "success": false,
        "skipped": false
      }
    }
  ],
  "config": {
    "memory_enabled": true,
    "rhythm_enabled": true,
    "aphasia_enabled": true,
    "strict_policy": false,
    "relaxed_policy": false,
    "fixtures_path": "tests/fixtures/ablation_prompts.json"
  },
  "errors": []
}
```

## Fixtures Format

Test fixtures are defined in `tests/fixtures/ablation_prompts.json`:

```json
{
  "version": "1.0.0",
  "description": "Ablation evaluation test fixtures",
  "prompts": [
    {
      "id": "unique_id",
      "prompt": "The actual prompt text",
      "expected_safe": true,
      "expected_quality": "high",
      "category": "educational",
      "expected_aphasic": false,
      "memory_fact": "optional fact for memory tests"
    }
  ]
}
```

### Fixture Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier for the prompt |
| `prompt` | Yes | The prompt text to evaluate |
| `expected_safe` | Yes | Whether the prompt should pass policy checks |
| `expected_quality` | No | Expected quality level: `high`, `medium`, `low`, `blocked` |
| `category` | No | Category for grouping: `educational`, `prompt_injection`, etc. |
| `expected_aphasic` | No | Whether the prompt exhibits aphasic patterns |
| `memory_fact` | No | Fact for memory store/recall tests |

## Adding New Ablation Modes

To add a new ablation mode:

1. Add the mode name to `AblationRunner.VALID_MODES` in `scripts/eval/run_ablation.py`

2. Add mode handling in `__init__`:
```python
self._new_component_enabled = mode != "no_new_component"
```

3. Add lazy-loading for the component:
```python
def _get_new_component(self) -> Any:
    if self._new_component is None and self._new_component_enabled:
        from mlsdm.new_module import NewComponent
        self._new_component = NewComponent()
    return self._new_component
```

4. Update `_process_prompt` to use the component

5. Add mode to the config output

6. Add test in `tests/eval/test_ablation_runner.py`

## Reproducibility

The ablation runner ensures reproducible results through:

1. **Fixed Seed**: The `--seed` parameter sets random seeds for:
   - Python's `random` module
   - NumPy's random number generator
   - PyTorch (if available)

2. **Deterministic Hash**: Each report includes a SHA256 hash of all outputs,
   allowing verification that runs with the same seed produce identical results.

3. **Fixed Fixtures**: Test prompts are loaded from JSON files with known content.

### Verifying Determinism

```bash
# Run twice with same seed
python scripts/eval/run_ablation.py --mode baseline --seed 42 --output-dir /tmp/run1
python scripts/eval/run_ablation.py --mode baseline --seed 42 --output-dir /tmp/run2

# Compare deterministic hashes
jq '.metrics.deterministic_hash' /tmp/run1/*.json
jq '.metrics.deterministic_hash' /tmp/run2/*.json
```

## Interpreting Results

### Comparing Ablation Modes

To evaluate component contribution, compare metrics between `baseline` and
ablation modes:

| Comparison | What It Shows |
|------------|---------------|
| baseline vs no_memory | Memory module contribution to retrieval |
| baseline vs no_rhythm | Rhythm contribution to system behavior |
| baseline vs no_aphasia | Aphasia detection effectiveness |
| baseline vs strict_policy | False block rate increase |
| baseline vs relaxed_policy | False allow rate increase |

### Expected Behaviors

- **no_memory**: `retrieval_hit_rate` should be 0 or undefined
- **no_rhythm**: Rhythm-dependent behaviors should be absent
- **no_aphasia**: `detection_accuracy` should be 0 or undefined
- **strict_policy**: Higher `violation_rate`, potentially higher `false_block`
- **relaxed_policy**: Lower `violation_rate`, potentially higher `false_allow`

## CI Integration

The ablation smoke test is integrated into CI via the workflow step. See
`.github/workflows/ci-smoke.yml` for the configuration.

```yaml
- name: Run ablation smoke test
  run: |
    python scripts/eval/run_ablation.py --mode baseline --seed 42 --quiet
```

## Troubleshooting

### "Fixtures file not found"

Ensure you're running from the repository root:
```bash
cd /path/to/mlsdm
python scripts/eval/run_ablation.py --mode baseline
```

Or specify the fixtures path explicitly:
```bash
python scripts/eval/run_ablation.py --fixtures tests/fixtures/ablation_prompts.json
```

### Non-zero Exit Code

The runner exits with code 1 if:
- Any exceptions occurred during evaluation
- Report contains errors

Check the `errors` field in the JSON report for details.

### Inconsistent Hashes

If deterministic hashes differ between runs with the same seed:
1. Check that no external randomness is involved
2. Verify the same fixtures file is used
3. Ensure no concurrent modifications to fixtures
