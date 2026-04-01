# `check_coverage_gate.py`

## Purpose
UNKNOWN/TBD: missing module docstring.

## Inputs
- Invocation: `python -m scripts.check_coverage_gate --help`
- CLI flags (static scan): --baseline; --coverage-xml; --tolerance

## Outputs
- `coverage.xml`
- `quality/coverage_gate.json`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.check_coverage_gate --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
