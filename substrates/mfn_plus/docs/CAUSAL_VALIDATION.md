# Causal Validation Gate

## Overview

The Causal Validation Gate verifies that every high-level conclusion of the MFN pipeline follows from data, invariants, and rules — not merely from type compatibility or local heuristics.

It sits between computation and publication: after `detect/forecast/compare` but before `manifest/report` finalization.

## Modes

| Mode | Behavior |
|------|----------|
| `strict` (default) | ERROR/FATAL → FAIL, blocks report |
| `observe` | Logs all violations, never blocks |
| `permissive` | Only FATAL blocks |

## Rule Catalog

### Simulation (SIM-001 → SIM-010)

| Rule | Severity | What it checks |
|------|----------|---------------|
| SIM-001 | FATAL | Field finite (no NaN/Inf) |
| SIM-002 | ERROR | Field min >= -95 mV |
| SIM-003 | ERROR | Field max <= +40 mV |
| SIM-004 | FATAL | History spatial shape matches field |
| SIM-005 | FATAL | History finite |
| SIM-006 | WARN | Last history frame ≈ final field |
| SIM-007 | ERROR | Alpha <= CFL limit (0.25) |
| SIM-008 | ERROR | Occupancy sum = 1.0 |
| SIM-009 | ERROR | Effective inhibition >= 0 |
| SIM-010 | WARN | SimulationSpec attached |

### Extraction (EXT-001 → EXT-006)

| Rule | Severity | What it checks |
|------|----------|---------------|
| EXT-001 | FATAL | Embedding non-empty and finite |
| EXT-002 | ERROR | Descriptor version set |
| EXT-003 | WARN | Instability index ≈ field CV |
| EXT-004 | ERROR | Stability keys complete |
| EXT-005 | ERROR | Complexity keys complete |
| EXT-006 | ERROR | Connectivity keys complete |

### Detection (DET-001 → DET-008)

| Rule | Severity | What it checks |
|------|----------|---------------|
| DET-001 | ERROR | Score in [0, 1] |
| DET-002 | ERROR | Anomaly label valid |
| DET-003 | ERROR | Regime label valid |
| DET-004 | ERROR | Confidence in [0, 1] |
| DET-005 | WARN | Contributing features ⊆ evidence keys |
| DET-006 | WARN | pathological_noise → noise evidence >= 0.1 |
| DET-007 | WARN | reorganized → plasticity >= 0.05 |
| DET-008 | INFO | watch label near threshold margin |

### Forecast (FOR-001 → FOR-007)

| Rule | Severity | What it checks |
|------|----------|---------------|
| FOR-001 | ERROR | Horizon >= 1 |
| FOR-002 | ERROR | Predicted states finite |
| FOR-004 | ERROR | Uncertainty envelope non-empty |
| FOR-005 | ERROR | Benchmark metrics keys present |
| FOR-006 | WARN | Structural error <= 1.0 |
| FOR-007 | WARN | Damping in [0.80, 0.95] |

*Note: FOR-003 (predicted states within biophysical bounds) is reserved but not yet implemented.*

### Comparison (CMP-001 → CMP-006)

| Rule | Severity | What it checks |
|------|----------|---------------|
| CMP-001 | ERROR | Distance >= 0 |
| CMP-002 | ERROR | Cosine in [-1, 1] |
| CMP-003 | ERROR | Label valid |
| CMP-004 | WARN | near-identical → distance < 0.5 |
| CMP-005 | WARN | divergent → cosine < 0.95 |
| CMP-006 | ERROR | Topology↔reorganization mapping consistent |

### Cross-Stage (XST-001 → XST-003)

| Rule | Severity | What it checks |
|------|----------|---------------|
| XST-001 | WARN | stable ≠ anomalous |
| XST-002 | WARN | disabled neuromod → zero plasticity |
| XST-003 | WARN | noise profile + reorganized → connectivity evidence |

### Perturbation (PTB-001 → PTB-002)

| Rule | Severity | What it checks |
|------|----------|---------------|
| PTB-001 | INFO | Anomaly label stable under 1e-6 noise |
| PTB-002 | INFO | Regime label stable under 1e-6 noise |

## Failure Semantics

- **PASS**: All rules pass. Report published.
- **DEGRADED**: Warnings present. Report published with `causal_validation.json` showing warnings.
- **FAIL**: Errors/fatals present. Report blocked with RuntimeError. No artifacts published.

## Artifact

Every report includes `causal_validation.json`:

```json
{
  "schema_version": "mfn-causal-validation-v1",
  "decision": "pass",
  "ok": true,
  "error_count": 0,
  "warning_count": 0,
  "runtime_hash": "c0a1c3cf4283b335",
  "config_hash": "a1b2c3d4e5f6g7h8",
  "all_rules": [
    {"rule_id": "SIM-001", "passed": true, "severity": "fatal", ...},
    ...
  ]
}
```

## Release Criteria

A release artifact is authoritative only if:
1. `causal_validation.json` present in manifest
2. `decision` is `pass` or `degraded`
3. `error_count` is 0
4. Perturbation rules (PTB-*) pass for baseline scenarios
5. Config hash matches versioned `configs/causal_validation_v1.json`

## Non-Goals

- Does not prove external truth — only internal logical correctness
- Does not replace simulation engine or detection strategy
- Does not add latency-critical runtime checks
