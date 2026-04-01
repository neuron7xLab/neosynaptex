# Traceability

| spec | schema | code | test | doc | status |
|---|---|---|---|---|---|
| docs/SPEC.md | schemas/experiment.schema.json | src/bnsyn/experiments/declarative.py | tests/test_declarative_experiments.py | docs/INPUTS.md | OK |
| docs/SPEC.md | schemas/readiness_report.schema.json | scripts/release_readiness.py | tests/test_release_readiness.py | docs/RELEASE_READINESS.md | OK |
| claims/claims.yml | — | scripts/validate_claims.py | tests/test_validate_claims.py | docs/GOVERNANCE.md | OK |
| docs/TESTING.md | quality/coverage_gate.json | scripts/check_coverage_gate.py | tests/test_check_coverage_gate.py | docs/ENFORCEMENT_MATRIX.md | OK |
| docs/PROJECT_SURFACES.md | schemas/experiment.schema.json | scripts/discover_public_surfaces.py | — | docs/API_STABILITY.md | GAP |
| docs/INDEX.md | — | scripts/check_internal_links.py | tests/test_check_internal_links.py | docs/ENFORCEMENT_MATRIX.md | OK |

## Validator
- Run `python -m scripts.validate_traceability`.
- Run `python -m scripts.check_internal_links`.
- Fails closed on malformed headers, empty rows/cells, or unsupported status.
