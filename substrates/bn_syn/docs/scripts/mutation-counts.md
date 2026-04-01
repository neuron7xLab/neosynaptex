# `mutation_counts.py`

## Purpose
Canonical mutation metrics model and extraction for CI and gates.

## Inputs
- Invocation: `python -m scripts.mutation_counts --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `quality/mutation_baseline.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.mutation_counts --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
