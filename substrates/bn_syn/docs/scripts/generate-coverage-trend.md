# `generate_coverage_trend.py`

## Purpose
Generate compact coverage trend artifacts for CI observability.

## Inputs
- Invocation: `python -m scripts.generate_coverage_trend --help`
- CLI flags (static scan): --branch; --coverage-json; --output-csv; --output-json; --sha

## Outputs
- UNKNOWN/TBD: no explicit output path literals found in static scan.

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.generate_coverage_trend --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
