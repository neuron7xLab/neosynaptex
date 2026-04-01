# `collect_ci_run_urls.py`

## Purpose
UNKNOWN/TBD: missing module docstring.

## Inputs
- Invocation: `python -m scripts.collect_ci_run_urls --help`
- CLI flags (static scan): --get; --out; --repo; --required; --sha

## Outputs
- `.github/workflows/ci-pr-atomic.yml`
- `.github/workflows/dependency-review.yml`
- `.github/workflows/math-quality-gate.yml`
- `.github/workflows/workflow-integrity.yml`
- `artifacts/audit/runs_for_head.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.collect_ci_run_urls --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
