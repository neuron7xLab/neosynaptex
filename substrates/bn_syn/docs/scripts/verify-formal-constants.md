# `verify_formal_constants.py`

## Purpose
Verify formal specification constants match code reality. This governance gate ensures that formal verification models (TLA+, Coq) use the same constants as the actual code, preventing spec drift. Checks: 1. TLA+ BNsyn.cfg constants vs src/bnsyn/config.py 2. Coq BNsyn_Sigma.v constants vs src/bnsyn/config.py Usage: python -m scripts.verify_formal_constants Exit codes: 0: All constants match 1: Mismatches found

## Inputs
- Invocation: `python -m scripts.verify_formal_constants --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- UNKNOWN/TBD: no explicit output path literals found in static scan.

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.verify_formal_constants --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
