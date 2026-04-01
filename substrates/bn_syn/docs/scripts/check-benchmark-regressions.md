# `check_benchmark_regressions.py`

## Purpose
Regression gate for physics and kernel benchmarks. Compares current benchmark results against committed baselines and fails when performance regresses beyond a configured threshold.

## Inputs
- Invocation: `python -m scripts.check_benchmark_regressions --help`
- CLI flags (static scan): --format; --kernel-baseline; --kernel-current; --physics-baseline; --physics-current; --threshold

## Outputs
- `benchmarks/baselines/kernel_profile.json`
- `benchmarks/baselines/physics_baseline.json`
- `benchmarks/kernel_profile.json`
- `benchmarks/physics_baseline.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.check_benchmark_regressions --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
