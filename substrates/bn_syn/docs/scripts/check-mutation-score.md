# `check_mutation_score.py`

## Purpose
Check mutation score against baseline with tolerance.

## Inputs
- Invocation: `python -m scripts.check_mutation_score --help`
- CLI flags (static scan): --advisory; --strict

## Outputs
- `quality/mutation_baseline.json`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.check_mutation_score --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
