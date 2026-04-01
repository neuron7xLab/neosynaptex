# `profile_kernels.py`

## Purpose
Kernel profiler for BN-Syn throughput analysis. This script instruments and profiles major computational kernels to identify bottlenecks and scaling surfaces for optimization. Parameters ---------- --output : str Path to output JSON file (default: benchmarks/kernel_profile.json) --seed : int Random seed for deterministic reproduction (default: 42) --neurons : int Number of neurons in the network (default: 200) --dt : float Timestep in milliseconds (default: 0.1) --steps : int Number of simulation steps (default: 1000) Returns ------- None Writes JSON with kernel metrics to file or stdout Notes ----- This creates the "Performance Jacobian" - the gradient of computational cost with respect to each kernel operation. References ---------- Problem statement STEP 2

## Inputs
- Invocation: `python -m scripts.profile_kernels --help`
- CLI flags (static scan): --dt; --neurons; --output; --repeats; --seed; --steps; --warmup

## Outputs
- `benchmarks/kernel_profile.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.profile_kernels --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
