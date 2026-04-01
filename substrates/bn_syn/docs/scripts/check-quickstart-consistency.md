# `check_quickstart_consistency.py`

## Purpose
Validate canonical install/quickstart commands stay consistent across docs.

## Inputs
- Invocation: `python -m scripts.check_quickstart_consistency --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `README.md`
- `docs/LEGENDARY_QUICKSTART.md`
- `docs/QUICKSTART.md`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.check_quickstart_consistency --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
