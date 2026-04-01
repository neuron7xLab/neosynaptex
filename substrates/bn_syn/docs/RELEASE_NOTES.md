# Release Notes

## Release Candidate

This release candidate focuses on verifiable readiness for a public demo with
deterministic behavior, build/install validation, and audit-grade evidence.

### Verified in this RC

- **Quality gates**: `make check` (format, lint, mypy, coverage, SSOT, security).
- **Test gates**: `make test` (non-validation suite).
- **Coverage**: ≥95% line coverage for `src/bnsyn` with JSON report.
- **Determinism**: three consecutive non-validation test runs.
- **Packaging**: `pip install -e ".[dev]"` and `python -m build`.
- **Security evidence**: gitleaks, pip-audit, and bandit logs captured.
- **Mutation baseline**: generated from real mutmut results (score 0.0%; see Risks).

See `artifacts/release_rc/` for the command logs and reports used as evidence.

### Risks & Mitigations

- **Mutation score is 0.0% (all mutants survived)** — indicates weak mutation-killing assertions
  for critical modules. Mitigation: prioritize mutation hardening on the four scoped modules and
  re-run `make mutation-check-strict` nightly. Rollback: revert to previous baseline commit if
  mutation tooling causes instability for release, but keep status and evidence intact.
