# `validate_codebase_readiness_audit.py`

## Purpose
Validate codebase readiness audit JSON structure and scoring invariants.

## Inputs
- Invocation: `python -m scripts.validate_codebase_readiness_audit --help`
- CLI flags (static scan): --path

## Outputs
- `docs/appendix/codebase_readiness_audit_2026-02-15.json`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.validate_codebase_readiness_audit --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
