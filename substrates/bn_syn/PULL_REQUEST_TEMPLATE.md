## Background & Motivation
This change finalizes the regime-control subsystem for audit-grade readiness with strict contracts, governance, and reproducibility artifacts.

## Technical Changes
- Added formal regime controller specification and FMEA.
- Added runtime validation, structured logging, and ledger provenance.
- Added release gate and expanded test suites (property/golden/performance/simulation/governance).

## Testing Strategy & Evidence
- `make check`
- `python scripts/check_regime_release_gate.py`
- `pytest --cov=src/bnsyn --cov-report=xml:coverage.xml --cov-fail-under=100 -q`

## Risk Assessment & FMEA Summary
Primary risks: non-finite update drift, malformed activation windows, governance drift, ledger write failures.
Mitigation summary in `docs/fmea/regime_control_loop_fmea.md`.

## Observability & Monitoring
Structured JSON logs from release gate and ledger append outcomes; UTC timestamps enforced.

## Rollback & Kill-switch
- Kill-switch: set `learning_rate=0` or bypass `RegimeController`.
- Rollback: `git revert <commit_sha>`.

## Open Questions
- Whether gamma proxy biological interpretation can be elevated from HYPOTHESIS to TESTED with external datasets.
