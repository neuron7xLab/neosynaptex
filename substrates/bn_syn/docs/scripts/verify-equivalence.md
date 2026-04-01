# `verify_equivalence.py`

## Purpose
Physical equivalence verification for BN-Syn backends. This script compares reference vs accelerated backends to ensure physics-preserving transformations maintain exact emergent dynamics within specified tolerances. Parameters ---------- --reference : str Path to reference backend physics baseline JSON --accelerated : str Path to accelerated backend physics baseline JSON --output : str Path to output equivalence report markdown (default: benchmarks/equivalence_report.md) --tolerance : float Maximum allowed relative deviation (default: 0.01 = 1%) Returns ------- None Writes equivalence report markdown to file Notes ----- This is the CRITICAL validation step. If physics diverges beyond tolerance, the accelerated backend MUST be reverted. References ---------- Problem statement STEP 5

## Inputs
- Invocation: `python -m scripts.verify_equivalence --help`
- CLI flags (static scan): ---; --accelerated; --output; --reference; --tolerance

## Outputs
- `benchmarks/equivalence_report.md`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.verify_equivalence --help
```

## Failure Modes
- Returns exit code 1 when validation conditions fail.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
