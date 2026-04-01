# `orchestrate_throughput_scaling.py`

## Purpose
Master orchestrator for BN-Syn throughput scaling validation. This script executes the complete 7-step physics-preserving optimization workflow: 1. Generate ground-truth baseline 2. Profile kernels 3. Analyze scaling surfaces (already documented in scaling_plan.md) 4. Run accelerated backend 5. Verify physics equivalence 6. Calculate throughput gains 7. Generate comprehensive report Parameters ---------- --steps : int Number of simulation steps (default: 1000) --neurons : int Number of neurons (default: 200) --tolerance : float Physics equivalence tolerance (default: 0.01 = 1%) --output-dir : str Output directory for all reports (default: benchmarks/) Returns ------- None Generates complete validation suite Notes ----- This is the master orchestrator for physics-preserving throughput scaling. References ---------- Problem statement: All 7 steps

## Inputs
- Invocation: `python -m scripts.orchestrate_throughput_scaling --help`
- CLI flags (static scan): --accelerated; --backend; --neurons; --output; --output-dir; --reference; --steps; --tolerance

## Outputs
- `.github/workflows/physics-equivalence.yml`
- `equivalence_report.md`
- `kernel_profile.json`
- `physics_accelerated.json`
- `physics_baseline.json`
- `scaling_plan.md`
- `throughput_gain.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.orchestrate_throughput_scaling --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
