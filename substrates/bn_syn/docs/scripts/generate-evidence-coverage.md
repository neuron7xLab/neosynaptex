# `generate_evidence_coverage.py`

## Purpose
Generate EVIDENCE_COVERAGE.md from claims.yml and bibliography. This script produces a deterministic evidence coverage table showing traceability for each claim in the registry. Output: docs/EVIDENCE_COVERAGE.md

## Inputs
- Invocation: `python -m scripts.generate_evidence_coverage --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `EVIDENCE_COVERAGE.md`
- `claims.yml`

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.generate_evidence_coverage --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
