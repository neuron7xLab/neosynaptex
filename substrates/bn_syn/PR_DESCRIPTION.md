## Intent
Formalize repository documentation so a new engineer can onboard quickly, discover architecture/API surfaces, and operate every `scripts/*.py` command with evidence-backed references.

## Scope
- Added a canonical **Start Here** onboarding page and wired a stable docs navigation spine in Sphinx.
- Added a deterministic **Scripts Reference** registry with 100% coverage of `scripts/*.py`, plus generated help-output artifacts for scripts that expose `--help`.
- Added a **Module Responsibility Matrix** mapping package/module responsibilities to entrypoints and invariants.
- Added **Build Documentation Locally** guidance with setup/build/linkcheck commands and generated-artifact notes.
- Updated README and docs index navigation to point to onboarding, scripts, API docs, and docs-build instructions.

## Assumptions
- Target platform assumed Linux (default).
- Allowed commands assumed read/build/test/docs and script `--help` probes.
- Existing Sphinx/docstring warnings were treated as pre-existing unless introduced by this change.

## Commands Run
- `python -m pip install -e '.[dev]'`
- `python - <<'PY' ...` (scripts coverage validation: verify every `scripts/*.py` appears in `docs/SCRIPTS/index.md`)
- `python -m sphinx -b html docs docs/_build/html`
- `python -m sphinx -b linkcheck docs docs/_build/linkcheck`
- `pytest -q tests/test_scan_governed_docs_script.py tests/test_quickstart_consistency_script.py tests/test_cli_smoke.py`

## Verification Results
- Scripts coverage check: **PASS** (`scripts_total 63`, `missing []`).
- Sphinx HTML build: **PASS** (build succeeded).
- Sphinx linkcheck: **PASS** (build succeeded; external links resolved in this run).
- Targeted regression tests: **PASS** (6 passed).

## Compatibility Notes
- No runtime behavior changes to `src/` modules.
- Changes are documentation-only plus generated help artifacts under `docs/_generated/script_help/`.
