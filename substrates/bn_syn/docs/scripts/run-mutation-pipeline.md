# `run_mutation_pipeline.py`

## Purpose
Run mutmut with crash/survivor-aware fail-closed semantics.

## Inputs
- Invocation: `python -m scripts.run_mutation_pipeline --help`
- CLI flags (static scan): --paths-to-mutate; --results-file; --results-stderr-file; --runner; --status; --survivors-file; --tests-dir

## Outputs
- `mutation_results.stderr.txt`
- `mutation_results.txt`
- `survived_mutants.txt`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.run_mutation_pipeline --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
