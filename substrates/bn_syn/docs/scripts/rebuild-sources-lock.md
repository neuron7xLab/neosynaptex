# `rebuild_sources_lock.py`

## Purpose
UNKNOWN/TBD: missing module docstring.

## Inputs
- Invocation: `python -m scripts.rebuild_sources_lock --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `mapping.yml`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.rebuild_sources_lock --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
