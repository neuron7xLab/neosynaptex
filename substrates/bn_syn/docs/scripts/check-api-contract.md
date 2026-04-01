# `check_api_contract.py`

## Purpose
Semver-aware API contract gate for BN-Syn public modules.

## Inputs
- Invocation: `python -m scripts.check_api_contract --help`
- CLI flags (static scan): --baseline; --baseline-version; --current-version; --write-baseline

## Outputs
- UNKNOWN/TBD: no explicit output path literals found in static scan.

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.check_api_contract --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
