# READINESS REPORT

- Repository: `bnsyn-phase-controlled-emergent-dynamics`
- HEAD SHA: `a9a4c9b24bde5de8c8f6ff12d1ce19295500c22a`
- Timestamp (UTC): `2026-02-15T17:51:35.870473+00:00`
- Python: `Python 3.12.12`

## VERIFIED READINESS: **85%** (lower-bound, evidence-backed)

## Score Breakdown

| Criterion | Points | Status | Evidence | Notes |
|---|---:|---|---|---|
| A1 | 10/10 | PASS | `checks.A1_install_clean_venv` | - |
| A2 | 5/5 | PASS | `checks.A2_import_smoke` | - |
| A3 | 5/5 | PASS | `checks.A3_cli_smoke` | - |
| B1 | 15/15 | PASS | `checks.B1_make_test` | - |
| B2 | 5/5 | PASS | `checks.B2_subset_marker` | - |
| C1 | 5/5 | PASS | `checks.C1_validate_required_checks` | - |
| C2 | 5/5 | PASS | `checks.C2_validate_required_status_contexts` | - |
| C3 | 5/5 | PASS | `checks.C3_validate_mutation_baseline` | - |
| D1 | 10/10 | PASS | `checks.D1_release_readiness` | - |
| E1 | 5/5 | PASS | `checks.E1_quickstart_exact_commands` | - |
| E2 | 5/5 | PASS | `checks.E2_quickstart_smoke_target` | - |
| F1 | 0/15 | FAIL | `checks.F1_ci_proof` | Required workflow runs missing/success criteria unmet for HEAD (summary={'success': 0, 'not_triggered': 1, 'missing': 3, 'required_total': 4, 'pass': False}). |
| G1 | 5/5 | PASS | `checks.G_files` | Explicit dependency metadata and lock file present. |
| G2 | 5/5 | PASS | `checks.G_files` | LICENSE present; SECURITY.md also present. |

**Earned:** 85/100  
**Unknown bucket:** 0 points  
**Potential max (if unknown resolved):** 85/100

## Top blockers

- `F1` missing `15` points — Required workflow runs missing/success criteria unmet for HEAD (summary={'success': 0, 'not_triggered': 1, 'missing': 3, 'required_total': 4, 'pass': False}).

## Repro steps (exact commands)

- `mkdir -p artifacts/readiness`
- `python -V`
- `python -m pip --version`
- `uname -a || ver || systeminfo`
- `git rev-parse HEAD`
- `git status --porcelain`
- `ls -la`
- `find scripts -maxdepth 2 -type f -name "*.py" 2>/dev/null || true`
- `ls -la .github/workflows 2>/dev/null || true`
- `ls -la Makefile pyproject.toml setup.cfg setup.py requirements*.txt 2>/dev/null || true`
- `rg -n "quickstart|install|pip install|bnsyn" README* docs 2>/dev/null || true`
- `python -m venv .venv_readiness`
- `. .venv_readiness/bin/activate && python -m pip install -U pip`
- `. .venv_readiness/bin/activate && python -m pip install -e .`
- `. .venv_readiness/bin/activate && python -c "import bnsyn; print('import_ok', getattr(bnsyn,'__version__',None))"`
- `. .venv_readiness/bin/activate && python -m bnsyn --help`
- `python -m scripts.release_readiness`
- `python -m scripts.validate_required_checks`
- `python -m scripts.validate_required_status_contexts`
- `python -m scripts.validate_mutation_baseline`
- `make test`
- `python -m pytest -q -m "not validation and not property and not benchmark"`
- `. .venv_readiness/bin/activate && python -m pip install -e .`
- `. .venv_readiness/bin/activate && python -m bnsyn --help`
- `. .venv_readiness/bin/activate && bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32`
- `. .venv_readiness/bin/activate && make quickstart-smoke`
- `python -m scripts.collect_ci_run_urls --sha "$(git rev-parse HEAD)" --out artifacts/readiness/ci_runs.json`

## NEEDS_USER

- Push the HEAD commit to GitHub and trigger required workflows (`ci-pr-atomic`, `workflow-integrity`, `math-quality-gate`), then rerun collector command to obtain PASS-level CI executability proof for this SHA.
