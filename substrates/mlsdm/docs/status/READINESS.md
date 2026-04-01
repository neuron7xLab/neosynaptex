# Readiness Status

**Last Updated:** January 2025  
**Document Version:** 1.0.0

## Source of Truth

The canonical source of readiness truth is:

1. **CI Workflows** — `.github/workflows/*.yml`
2. **Verification Scripts** — `scripts/verify_*.py`
3. **Evidence Artifacts** — `artifacts/evidence/`

## Readiness Gates

The following CI workflows form the readiness gates:

| Gate | Workflow | Description |
|------|----------|-------------|
| CI Smoke Tests | `ci-smoke.yml` | Core integration tests and linting |
| Production Gate | `prod-gate.yml` | Production readiness validation |
| Performance & Resilience | `perf-resilience.yml` | Performance benchmarks and resilience tests |
| Property-Based Tests | `property-tests.yml` | Hypothesis-based property tests |
| SAST Security Scan | `sast-scan.yml` | Static application security testing |

**Supporting Workflows:**

| Workflow | Description |
|----------|-------------|
| `coverage-badge.yml` | Coverage measurement and badge generation |
| `readiness-evidence.yml` | Evidence snapshot capture |

## Local Validation

To validate readiness locally:

```bash
# Verify documentation contracts
make verify-docs

# Verify security skip path invariants
make verify-security-skip

# Run linting
make lint

# Run type checking
make type

# Run tests
make test

# Run coverage gate (default threshold: 75%)
make coverage-gate
```

## Evidence Pipeline

Evidence snapshots are captured by the `readiness-evidence.yml` workflow and stored under `artifacts/evidence/`. To capture evidence locally:

```bash
make evidence
make verify-metrics
```

## Status

Readiness levels are not claimed without dated evidence artifacts. Refer to:

- [CI workflow results](https://github.com/neuron7xLab/mlsdm/actions) for current gate status
- `artifacts/evidence/` for evidence snapshots
- `scripts/evidence/verify_evidence_snapshot.py` for verification logic
