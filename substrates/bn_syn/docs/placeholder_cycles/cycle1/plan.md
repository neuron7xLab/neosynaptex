# CYCLE 1 — Plan (Planner) + Acceptance Map

## Scope Compression (minimum viable scope)

Cycle 1 changes are constrained to:

1. Files that currently contain normalized PH entries in `docs/PLACEHOLDER_REGISTRY.md`:
   - `src/bnsyn/emergence/crystallizer.py` (PH-0001)
   - `tests/test_coverage_gate.py` (PH-0002)
   - `tests/validation/test_chaos_integration.py` (PH-0003)
2. Directly dependent test or validation infrastructure required to prove PH closure:
   - `scripts/scan_placeholders.py`
   - `tests/test_scan_placeholders.py`
   - `docs/PLACEHOLDER_REGISTRY.md`

No additional modules are in scope unless required to keep tests deterministic and CI-green.

## PH_BATCHES

### PH_BATCH_01 — Runtime-critical emergence path
- Module/context: `bnsyn.emergence.crystallizer`
- PH included:
  - PH-0001
- Rationale: isolates runtime-critical fallback behavior in crystallizer edge handling.

### PH_BATCH_02 — Test harness placeholder guards
- Module/context: test and validation harness
- PH included:
  - PH-0002
  - PH-0003
- Rationale: both findings are `pass_in_except` in tests; can be remediated with explicit fail-closed assertions.

## PH Assignment Matrix

| PH ID | File | fix_strategy | test_strategy | Notes |
|---|---|---|---|---|
| PH-0001 | `src/bnsyn/emergence/crystallizer.py` | `guard_fail_closed` | `regression` | Replace implicit `pass` fallback with deterministic explicit state retention branch and auditable warning path. |
| PH-0002 | `tests/test_coverage_gate.py` | `implement_minimal` | `regression` | Replace permissive `pass` with explicit assertion for missing coverage artifact behavior. |
| PH-0003 | `tests/validation/test_chaos_integration.py` | `guard_fail_closed` | `regression` | Replace permissive `pass` with explicit finite-output and accepted-error assertions. |

## Delivery Sequence

1. Close PH_BATCH_01 (runtime-critical) first, execute targeted regression tests.
2. Close PH_BATCH_02, execute targeted regression tests.
3. Run meta-scan, registry validation, and CI-equivalent local checks.
4. Update PH registry statuses and attach evidence artifacts.

## Exit Criteria

- Every PH in Cycle 1 is set to `RESOLVED` with linked test evidence.
- Placeholder scan reports zero actionable findings.
- Registry schema and uniqueness checks pass.
- CI-required checks are green.
