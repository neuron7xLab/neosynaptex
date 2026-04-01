# `benchmark_physics.py`

## Purpose
Ground-truth physics benchmark for BN-Syn throughput scaling. This script establishes the performance manifold baseline that all optimizations must preserve. It measures biophysical throughput under fixed deterministic conditions. Parameters ---------- --backend : str Execution backend: 'reference' (default) or 'accelerated' --output : str Path to output JSON file (default: benchmarks/physics_baseline.json) --seed : int Random seed for deterministic reproduction (default: 42) --neurons : int Number of neurons in the network (default: 200) --dt : float Timestep in milliseconds (default: 0.1) --steps : int Number of simulation steps (default: 1000) Returns ------- None Writes JSON with ground-truth metrics to file or stdout Notes ----- This benchmark is the SSOT (Single Source of Truth) for physics-preserving optimization. All acceleration must match these results within tolerance. References ---------- docs/SPEC.md#P2-11 Problem statement STEP 1

## Inputs
- Invocation: `python -m scripts.benchmark_physics --help`
- CLI flags (static scan): --backend; --dt; --neurons; --output; --seed; --steps

## Outputs
- `benchmarks/physics_baseline.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.benchmark_physics --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
