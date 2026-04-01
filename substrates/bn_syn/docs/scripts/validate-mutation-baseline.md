# `validate_mutation_baseline.py`

## Purpose
Validate mutation baseline schema contract (fail-closed).

## Inputs
- Invocation: `python -m scripts.validate_mutation_baseline --help`
- CLI flags (static scan): --baseline

## Outputs
- `quality/mutation_baseline.json`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.validate_mutation_baseline --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
