# Pytest Failure Diagnostics

## Source of truth
Pytest remains the only pass/fail source of truth. Diagnostics are additive and never convert a failing suite into a passing one.

## Authoritative orchestration path
Both local and CI use the same authoritative runner:
- `python -m scripts.run_pytest_with_diagnostics ...`

`make test-diagnostics` delegates to this runner.

The runner:
1. executes pytest,
2. captures JUnit XML + tee log,
3. always generates diagnostics,
4. returns `pytest_exit_code` when pytest fails, otherwise returns `diagnostics_exit_code` if diagnostics generation fails, otherwise `0`.

## Artifacts
The diagnostics contract emits:
- `artifacts/tests/failure-diagnostics.json` (schema-validated)
- `artifacts/tests/failure-diagnostics.md` (human/LLM-oriented)

Optional publication artifacts:
- `artifacts/tests/failure-annotations.txt` (artifact copy of annotation commands)

## CI publication behavior
In GitHub Actions reusable pytest workflow:
- diagnostics are generated from the authoritative runner step,
- `::error ...` workflow commands are emitted (bounded top-N) for UI annotations,
- diagnostics artifacts are uploaded on both success and failure,
- `$GITHUB_STEP_SUMMARY` gets a derived diagnostics summary section.

UI annotations and artifact annotation files are distinct outputs.

## Redaction policy
Redaction is bounded and deterministic. It applies only to published excerpts and never mutates raw JUnit/log source inputs.

Patterns include common token-like forms:
- `ghp_...`
- `github_pat_...`
- `Bearer ...`
- long hex / key-like blobs

This is practical masking, not perfect secret detection.

## Determinism and schema discipline
- Stable ordering for failures and annotations.
- Stable clipping behavior.
- No timestamps/host-specific payload fields.
- Normal payloads and fail-closed `input_error` payloads validate against `schemas/pytest-failure-diagnostics.schema.json`.

## Pytest passthrough
`run_pytest_with_diagnostics.py` supports robust pytest arg passthrough via either:
- unknown-arg forwarding, or
- explicit `--` separator.

This enables forwarding pytest flags beginning with `-` safely.
