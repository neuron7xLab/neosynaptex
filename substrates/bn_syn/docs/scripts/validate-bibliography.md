# `validate_bibliography.py`

## Purpose
Validate BN-Syn bibliography SSOT: - bnsyn.bib entries include DOI for Tier-A sources - mapping.yml is well-formed and references existing bibkeys - sources.lock lines are syntactically valid and SHA256 matches LOCK_STRING - tiers and claim mappings are consistent across claims/mapping

## Inputs
- Invocation: `python -m scripts.validate_bibliography --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `claims.yml`
- `mapping.yml`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.validate_bibliography --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
