# Noise Cleanup Report

## Scope
This run applied a fail-closed digital-noise audit and cleanup pass restricted to provable byproducts only.

## Expected Commands
- Tests: `python -m pytest -m "not validation" -q`
- Lint: `ruff check .`
- Lint: `pylint src/bnsyn`
- Typecheck: `mypy src --strict --config-file pyproject.toml`
- Build: `python -m build`

## Actions Taken
1. Captured baseline repository/toolchain status.
2. Built candidate set from ignored/untracked and deterministic cache/noise scans.
3. Classified candidates under T1–T4 rubric.
4. Performed dry-run safety checks (`git clean -ndX`, `git clean -nd`).
5. Ran quality gates.

## Deletion Summary
- Deleted: 0 paths.
- Kept: all non-candidate paths.
- Rationale: no path met the confidence=1.0 trash rubric in this run.

## Kept / Not Deleted
- `proof_bundle/logs/*` untracked evidence logs produced during this run were kept as audit artifacts.

## Quality Gates
- Tests: failed due to missing optional dependencies (`psutil`, `hypothesis`, `yaml`, `pylint`) in environment.
- Ruff: passed.
- Mypy: passed.
- Build: failed due to missing `build` module in environment.

## Evidence Pointers
- Candidate discovery: `proof_bundle/logs/103_ls_untracked_ignored.log`, `proof_bundle/logs/104_find_cache_dirs.log`, `proof_bundle/logs/105_find_noise_files.log`
- Dry-run validation: `proof_bundle/logs/106_dryrun_clean_ignored.log`, `proof_bundle/logs/107_dryrun_clean_all.log`
- Quality gates: `proof_bundle/logs/108_test_cmd.log`, `proof_bundle/logs/109_lint_ruff.log`, `proof_bundle/logs/110_lint_pylint.log`, `proof_bundle/logs/111_typecheck_mypy.log`, `proof_bundle/logs/112_build_cmd.log`
