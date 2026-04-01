# `release_readiness.py`

## Purpose
Generate a release readiness report for BN-Syn.

## Inputs
- Invocation: `python -m scripts.release_readiness --help`
- CLI flags (static scan): --advisory; --json-out; --md-out

## Outputs
- `CI_GATES.md`
- `GOVERNANCE_VERIFICATION_REPORT.md`
- `HARDENING_SUMMARY.md`
- `QUALITY_INFRASTRUCTURE.md`
- `README.md`
- `README_CLAIMS_GATE.md`
- `SECURITY.md`
- `TESTING_MUTATION.md`
- `VERIFICATION_REPORT.md`
- `artifacts/release_readiness.json`
- `artifacts/release_readiness.md`
- `baseline.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.release_readiness --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
