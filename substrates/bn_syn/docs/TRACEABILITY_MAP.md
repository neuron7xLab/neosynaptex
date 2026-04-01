# Traceability Map

Requirements and safety constraints are mapped to code entrypoints, tests, and CI gates.

| Requirement / Constraint | Hazard / Safety intent | Code entrypoint | Tests | CI gate |
|---|---|---|---|---|
| Reject malformed external numeric inputs (shape/dtype/non-finite) | Prevent undefined numerical state propagation | `src/bnsyn/validation/inputs.py` | `tests/test_validation_inputs.py` | `ci-pr-atomic` → `tests-smoke` |
| Enforce admissible simulation grid (`dt_ms`, duration multiple) | Prevent unstable/undefined integration schedules | `src/bnsyn/schemas/experiment.py` | `tests/test_schema_experiment_contracts.py` | `ci-pr-atomic` → `tests-smoke` |
| Wake-cycle API must reject invalid recording cadence | Prevent silent memory-capture corruption | `src/bnsyn/sleep/cycle.py` | `tests/test_sleep_cycle.py` | `ci-pr-atomic` → `tests-smoke` |
| Provenance generation must be deterministic without git availability | Preserve auditability in non-git execution contexts | `src/bnsyn/provenance/manifest_builder.py` | `tests/test_manifest_builder.py` | `ci-pr-atomic` → `tests-smoke` |
| Coverage must not regress below baseline/floor | Prevent quality drift | `scripts/check_coverage_gate.py`, `quality/coverage_gate.json` | `make coverage-gate` execution path | `ci-pr-atomic` reusable pytest + local gate command |

## Verification commands

```bash
python -m pytest -q
python -m pytest --cov=bnsyn --cov-report=term-missing:skip-covered --cov-report=xml:coverage.xml -q
python -m scripts.check_coverage_gate --coverage-xml coverage.xml --baseline quality/coverage_gate.json
```

Expected output patterns:
- tests: `... [100%]` + pass summary
- coverage: terminal missing-lines report + `Coverage XML written to file coverage.xml`
- gate: `PASS: coverage gate satisfied`
