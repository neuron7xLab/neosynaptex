# Emergence experiment pipeline

This feature restores an artifact-oriented emergence experiment path.

## CLI commands

- `bnsyn emergence-run` runs one deterministic experiment and writes:
  - NPZ artifact: `run_<seed>_Iext_<integer current>pA.npz`
  - report: `emergence_run_report.json`
- `bnsyn emergence-sweep` runs fixed external current values and writes:
  - report: `emergence_sweep_report.json`
- `bnsyn emergence-plot --input <npz> --output <png>` renders raster/rate/sigma views.

## Declarative config

`simulation` now supports:

- `external_current_pA` (default `0.0`)
- `artifact_dir` (default `null`)

If `artifact_dir` is set, declarative runs write NPZ artifacts using the emergence pipeline.
If `artifact_dir` is null, declarative runs use `run_simulation(...)` summary mode.
