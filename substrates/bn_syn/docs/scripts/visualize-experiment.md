# `visualize_experiment.py`

## Purpose
Visualize temperature ablation experiment results. This script generates publication-quality figures from experiment results. Usage ----- python -m scripts.visualize_experiment --run-id temp_ablation_v1 python -m scripts.visualize_experiment --run-id temp_ablation_v1 --results results/temp_ablation_v1 --out figures

## Inputs
- Invocation: `python -m scripts.visualize_experiment --help`
- CLI flags (static scan): --out; --results; --run-id

## Outputs
- `manifest.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.visualize_experiment --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
