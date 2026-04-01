# `mutation_ci_summary.py`

## Purpose
Emit canonical mutation CI outputs and GitHub summary.

## Inputs
- Invocation: `python -m scripts.mutation_ci_summary --help`
- CLI flags (static scan): --baseline; --write-output; --write-summary

## Outputs
- `quality/mutation_baseline.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.mutation_ci_summary --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
