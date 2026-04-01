# `lint_ci_truthfulness.py`

## Purpose
Lint CI workflows for truthfulness and quality. This governance gate scans GitHub Actions workflows for anti-patterns that could lead to false-green CI or policy drift: 1. Test/verification commands followed by `|| true` (masks failures) 2. Hard-coded "success" summaries not derived from actual outputs 3. Workflow inputs declared but never used 4. Missing permissions declarations (should be explicit and minimal) Usage: python -m scripts.lint_ci_truthfulness --out artifacts/ci_truthfulness.json --md artifacts/ci_truthfulness.md Exit codes: 0: All checks passed 1: Critical violations found 2: Warnings found (can be promoted to errors)

## Inputs
- Invocation: `python -m scripts.lint_ci_truthfulness --help`
- CLI flags (static scan): --md; --out; --strict; --workflows-dir

## Outputs
- UNKNOWN/TBD: no explicit output path literals found in static scan.

## Side Effects
- Writes files or directories during normal execution.

## Safety Level
- Writes artifacts only

## Examples
```bash
python -m scripts.lint_ci_truthfulness --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
