# Metrics Source of Truth

**Last Updated**: January 1, 2026
**Purpose**: Single source for test coverage and quality metrics to prevent documentation drift.

---

## Evidence Snapshots

Metrics are sourced from **committed evidence snapshots** in the repository for reproducibility. Latest snapshot: `artifacts/evidence/2025-12-26/2a6b52dd6fd4/`.

| Artifact | Path |
|----------|------|
| **Coverage Report** | `artifacts/evidence/<date>/<sha>/coverage/coverage.xml` |
| **JUnit Test Results** | `artifacts/evidence/<date>/<sha>/pytest/junit.xml` |
| **Logs** | `artifacts/evidence/<date>/<sha>/logs/` |
| **Manifest** | `artifacts/evidence/<date>/<sha>/manifest.json` |
| **Iteration Metrics (deterministic)** | `artifacts/evidence/<date>/<sha>/iteration/iteration-metrics.jsonl` |
| **Benchmarks (optional)** | `artifacts/evidence/<date>/<sha>/benchmarks/` |
| **Memory Footprint (optional)** | `artifacts/evidence/<date>/<sha>/memory/memory_footprint.json` |

Iteration metrics are produced by `make evidence` via the deterministic generator (`make iteration-metrics`).

Regenerate and validate locally:

```bash
make iteration-metrics    # deterministic iteration loop benchmark
make evidence            # captures and verifies the latest snapshot
make verify-metrics      # validate the latest snapshot without recapturing
# Raw commands (if needed):
python scripts/evidence/capture_evidence.py --mode build --inputs artifacts/tmp/evidence-inputs.json
python scripts/evidence/verify_evidence_snapshot.py --evidence-dir artifacts/evidence/<date>/<sha>/
ls artifacts/evidence/*/*
# Optional locals:
#   place benchmark-metrics.json or raw_neuro_engine_latency.json under ./benchmarks before capture
#   place memory_footprint.json under ./memory before capture
```
Latest evidence lives under: `artifacts/evidence/<date>/<sha>/`

---

## Coverage Metrics

| Metric | Value | Source |
|--------|-------|--------|
| **CI Coverage Threshold** | 75% | `coverage_gate.sh` + `.github/workflows/readiness-evidence.yml` |
| **Actual Coverage** | 80.04% | `artifacts/evidence/2025-12-26/2a6b52dd6fd4/coverage/coverage.xml` |

### Why 75% Threshold?

The CI coverage threshold (75%) is set to match the enforced gate in CI and `pyproject.toml`. It tracks the latest committed evidence and is raised only when sustained coverage exceeds the gate with comfortable headroom.

---

## Test Metrics

Test counts are derived from the committed JUnit evidence:

| Metric | Source |
|--------|--------|
| **Test Results** | `artifacts/evidence/<date>/<sha>/pytest/junit.xml` |

To get exact counts, parse the JUnit XML or run `make evidence`.

---

## Benchmark Metrics

Benchmark outputs are optional in evidence snapshot v1. When collected, they live under:

- `artifacts/evidence/<date>/<sha>/benchmarks/benchmark-metrics.json`
- `artifacts/evidence/<date>/<sha>/benchmarks/raw_neuro_engine_latency.json`

---

## CI Coverage Command

The canonical coverage command used in CI:

```bash
# Canonical coverage gate (also used by CI)
pytest --cov=src/mlsdm --cov-report=xml --cov-report=term-missing \
  --cov-fail-under=75 --ignore=tests/load -m "not slow and not benchmark" -v
```

**Use this exact command for local verification to match CI behavior.**

---

## Updating This Document

When evidence is regenerated:

1. Run `make evidence` to capture a new snapshot
2. Commit the new evidence folder under `artifacts/evidence/`
3. Update the "Last Updated" date above
4. If coverage exceeds threshold by 5%+ for 2+ releases, consider raising the threshold

---

## Related Documentation

- [TESTING_GUIDE.md](../TESTING_GUIDE.md) - How to write and run tests
- [CI_GUIDE.md](../CI_GUIDE.md) - CI/CD configuration overview
- [TEST_STRATEGY.md](../TEST_STRATEGY.md) - Test organization and priorities
- [Evidence README](../artifacts/evidence/README.md) - Evidence snapshot policy
