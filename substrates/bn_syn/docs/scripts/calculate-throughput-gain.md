# `calculate_throughput_gain.py`

## Purpose
Throughput gain calculator for BN-Syn optimization. This script calculates and records throughput improvements from physics-preserving transformations, creating an audit trail of performance gains. Parameters ---------- --reference : str Path to reference backend physics baseline JSON --accelerated : str Path to accelerated backend physics baseline JSON --output : str Path to output throughput gain JSON (default: benchmarks/throughput_gain.json) Returns ------- None Writes JSON with throughput metrics to file Notes ----- This creates the performance audit trail required for STEP 6. References ---------- Problem statement STEP 6

## Inputs
- Invocation: `python -m scripts.calculate_throughput_gain --help`
- CLI flags (static scan): --accelerated; --output; --reference

## Outputs
- `benchmarks/throughput_gain.json`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.calculate_throughput_gain --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
