# `compare_benchmarks.py`

## Purpose
Compare benchmark results against golden baseline. Detects performance regressions by comparing current benchmark results against the golden baseline stored in benchmarks/baselines/golden_baseline.yml. Exit codes: - 0: No significant regressions detected - 1: Regressions detected (>threshold%) Usage: python -m scripts.compare_benchmarks --baseline benchmarks/baselines/golden_baseline.yml \ --current benchmarks/baseline.json \ --format markdown

## Inputs
- Invocation: `python -m scripts.compare_benchmarks --help`
- CLI flags (static scan): --baseline; --current; --format

## Outputs
- `benchmarks/baseline.json`
- `benchmarks/baselines/golden_baseline.yml`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.compare_benchmarks --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
