# `generate_benchmark_baseline.py`

## Purpose
Generate benchmark baselines for the active regime.

## Inputs
- Invocation: `python -m scripts.generate_benchmark_baseline --help`
- CLI flags (static scan): --dt; --kernel-steps; --neurons; --output-dir; --physics-steps; --raw-dir; --runs; --seed; --warmup

## Outputs
- UNKNOWN/TBD: no explicit output path literals found in static scan.

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.generate_benchmark_baseline --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
