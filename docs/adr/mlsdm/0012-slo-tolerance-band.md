# ADR-0012: SLO Tolerance Band for CI Environments

**Status**: Accepted
**Date**: 2025-12-05
**Deciders**: MLSDM Core Team
**Categories**: Performance, CI/CD

## Context

Performance tests in CI environments exhibit 2-5% latency variance due to:
- VM virtualization overhead
- Shared CPU resources
- Background I/O contention

Strict P95 thresholds (150ms) cause intermittent failures even when production
performance remains stable.

## Decision

Introduce a 2% tolerance band for CI-only P95 latency checks while keeping
production monitoring strict.

Implementation details:
- `LatencySLO` exposes a `check_p95_compliance` helper that applies tolerance in CI.
- CI workflows set `MLSDM_DRIFT_LOGGING=silent` to reduce hot-path logging overhead.

## Consequences

### Positive

- CI stability improves without relaxing production SLO enforcement.
- Performance regressions still surface when exceeding the tolerance band.
- Drift telemetry remains intact while reducing noisy logging in CI.

### Negative

- Small regressions below 2% may not fail CI immediately.
- Requires periodic review to prevent tolerance creep.

## Alternatives Considered

1. **Increase base SLO thresholds**
   - Rejected: would weaken production monitoring.
2. **Remove performance tests from CI**
   - Rejected: loses early detection of regressions.

## References

- `docs/SLO_SPEC.md`
- `tests/perf/test_slo_api_endpoints.py`
