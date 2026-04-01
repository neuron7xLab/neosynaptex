# `validate_status_claims.py`

## Purpose
Validate public status and anti-overclaim policy for battle usage.

## Inputs
- Invocation: `python -m scripts.validate_status_claims --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `README.md`
- `STATUS.md`
- `docs/STATUS.md`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.validate_status_claims --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
