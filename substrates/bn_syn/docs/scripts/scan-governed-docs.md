# `scan_governed_docs.py`

## Purpose
Scan governed docs for untagged normative language. This script reads the authoritative governed docs list from docs/INVENTORY.md and scans for normative keywords and [NORMATIVE] tags. Rules: - Lines containing normative keywords must include [NORMATIVE][CLM-####] - Lines containing [NORMATIVE] must include a CLM-#### identifier Exit codes: - 0: All checks pass - 1: Governed docs could not be parsed or listed files missing - 2: Orphan normative statements found (missing [NORMATIVE][CLM-####])

## Inputs
- Invocation: `python -m scripts.scan_governed_docs --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `INVENTORY.md`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.scan_governed_docs --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
