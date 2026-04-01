# `_audit_metrics_pr40.py`

## Purpose
Independent metric audit for PR #40 temperature ablation experiment. This script independently computes metrics from raw trial data to verify the aggregated results reported in the PR.

## Inputs
- Invocation: `python -m scripts._audit_metrics_pr40 --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `results/_verify_runA/audit_metrics.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts._audit_metrics_pr40 --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
