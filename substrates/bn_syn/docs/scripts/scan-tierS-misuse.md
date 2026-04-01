# `scan_tierS_misuse.py`

## Purpose
Scan for misuse of Tier-S bibkeys in normative contexts. This script enforces the governance rule that Tier-S sources (bibkeys starting with 'tierS_') MUST NOT be used in normative contexts: - Lines tagged with [NORMATIVE] - Claims with normative=true in claims.yml Tier-S sources are for non-normative context/inspiration only.

## Inputs
- Invocation: `python -m scripts.scan_tierS_misuse --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `INVENTORY.md`
- `claims.yml`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.scan_tierS_misuse --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
