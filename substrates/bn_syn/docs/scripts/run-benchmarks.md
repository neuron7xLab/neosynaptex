# `run_benchmarks.py`

## Purpose
Run deterministic BN-Syn performance benchmarks.

## Inputs
- Invocation: `python -m scripts.run_benchmarks --help`
- CLI flags (static scan): --baseline; --output; --seed; --suite; --summary; --write-baseline

## Outputs
- `benchmarks/baseline.json`
- `benchmarks/results.json`
- `benchmarks/summary.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.run_benchmarks --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
