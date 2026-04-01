# `release_pipeline.py`

## Purpose
Deterministic release pipeline helper (changelog + version + build + dry-run publish).

## Inputs
- Invocation: `python -m scripts.release_pipeline --help`
- CLI flags (static scan): --apply-version-bump; --bump; --verify-only

## Outputs
- `CHANGELOG.md`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.release_pipeline --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
