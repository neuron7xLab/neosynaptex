# `validate_claims_coverage.py`

## Purpose
Validate Claims→Evidence Coverage (CLM-0011 Enforcement). Ensures all claims in claims.yml have complete bibliographic traceability: - bibkey (reference key) - locator (specific page/section in source) - verification_path (code/test that validates the claim) - status (claim lifecycle state) Exit codes: - 0: 100% coverage - 1: Incomplete coverage (<100%) Usage: python -m scripts.validate_claims_coverage --format markdown python -m scripts.validate_claims_coverage --format json

## Inputs
- Invocation: `python -m scripts.validate_claims_coverage --help`
- CLI flags (static scan): --format

## Outputs
- `claims/claims.yml`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.validate_claims_coverage --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
