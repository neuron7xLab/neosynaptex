# `validate_pr_gates.py`

## Purpose
UNKNOWN/TBD: missing module docstring.

## Inputs
- Invocation: `python -m scripts.validate_pr_gates --help`
- CLI flags (static scan): No static `--flag` tokens detected; inspect `main()` for positional args.

## Outputs
- `.github/PR_GATES.yml`
- `.github/WORKFLOW_CONTRACTS.md`
- `PR_GATES.yml`
- `ci-pr-atomic.yml`

## Side Effects
- No direct file-write calls detected in source.

## Safety Level
- Safe (read-only checks)

## Examples
```bash
python -m scripts.validate_pr_gates --help
```

## Failure Modes
- Any uncaught exception aborts execution with non-zero exit code.

## Interpretation Notes
- Validation scripts typically treat exit code `0` as pass and non-zero as contract drift or missing prerequisites.
- When purpose/outputs are `UNKNOWN/TBD`, inspect source code directly before production use.
