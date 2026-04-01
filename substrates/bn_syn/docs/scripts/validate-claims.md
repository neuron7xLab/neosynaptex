# `validate_claims.py`

## Purpose
UNKNOWN/TBD: missing module docstring.

## Inputs
- Invocation: `python -m scripts.validate_claims --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `bibliography/mapping.yml`
- `claims.yml`
- `claims/claims.yml`
- `mapping.yml`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.validate_claims --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
