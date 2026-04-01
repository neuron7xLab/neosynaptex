# `benchmark_production.py`

## Purpose
Local benchmark for BN-Syn production helpers. Not executed in CI. Intended for manual profiling. Run: python -m scripts.benchmark_production

## Inputs
- Invocation: `python -m scripts.benchmark_production --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- UNKNOWN/TBD: no explicit output path literals found in static scan.

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.benchmark_production --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
