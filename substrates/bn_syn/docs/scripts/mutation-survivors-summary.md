# `mutation_survivors_summary.py`

## Purpose
Append surviving mutants section to GitHub step summary.

## Inputs
- Invocation: `python -m scripts.mutation_survivors_summary --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `survived_mutants.txt`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.mutation_survivors_summary --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
