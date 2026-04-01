# `scan_placeholders.py`

## Purpose
Scan code/docs trees for placeholder signals used by governance gates.

## Inputs
- Invocation: `python -m scripts.scan_placeholders --help`
- CLI flags (static scan): --format

## Outputs
- Writes findings to stdout (`--format text` prints text to stderr, `--format json` emits JSON to stdout).

## Side Effects
- No repository file mutations; read-only scan.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.scan_placeholders --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
