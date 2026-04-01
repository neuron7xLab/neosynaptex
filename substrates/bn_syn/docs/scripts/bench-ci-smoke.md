# `bench_ci_smoke.py`

## Purpose
CI smoke test for benchmark harness. Runs minimal benchmark scenario to validate harness functionality. Not intended for performance measurement.

## Inputs
- Invocation: `python -m scripts.bench_ci_smoke --help`
- CLI flags (static scan): --json; --out; --repeats

## Outputs
- `results/ci_smoke.csv`
- `results/ci_smoke.json`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.bench_ci_smoke --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
