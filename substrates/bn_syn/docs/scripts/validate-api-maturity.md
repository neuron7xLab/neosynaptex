# `validate_api_maturity.py`

## Purpose
Validate package maturity status mapping for public BN-Syn modules.

## Inputs
- Invocation: `python -m scripts.validate_api_maturity --help`
- CLI flags (static scan): --path

## Outputs
- `docs/api_maturity.json`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.validate_api_maturity --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
