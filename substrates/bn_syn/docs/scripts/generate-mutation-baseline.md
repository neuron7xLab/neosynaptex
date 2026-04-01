# `generate_mutation_baseline.py`

## Purpose
Generate mutation testing baseline with real data.

## Inputs
- Invocation: `python -m scripts.generate_mutation_baseline --help`
- CLI flags (static scan): --reuse-cache; --runner

## Outputs
- `quality/mutation_baseline.json`

## Side Effects
- Writes files or directories during normal execution.
- Potential repository mutations detected (e.g., git/file synchronization workflows).

## Safety Level
- Mutates repository state

## Examples
```bash
python -m scripts.generate_mutation_baseline --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
