# EVIDENCE_INDEX

## File Evidence Pointers
1. `README.md:1-3` — "BN-Syn Thermostated Bio-AI System... deterministic reference implementation...".
2. `README.md:55-64` — "3-tier test selection strategy... Tier 1/2/3".
3. `pyproject.toml:1-7` — "name = 'bnsyn'... requires-python = '>=3.11'".
4. `pyproject.toml:14-33` — optional deps include `hypothesis`, `pytest`, `pytest-cov`, `pyyaml`, `psutil`.
5. `docs/ARCHITECTURE.md:11-18` — architecture traceability and control loops scope.
6. `docs/ARCHITECTURE_INVARIANTS.md:11-21` — strict input validation invariants.
7. `docs/ARCHITECTURE_INVARIANTS.md:44-57` — provenance and determinism controls.
8. `docs/CI_GATES.md:24-31` — blocking PR gates definition.
9. `docs/CI_GATES.md:53-74` — non-blocking validation and benchmark tiers.
10. `docs/TESTING.md:7-15` — install test deps + expected no import errors.
11. `docs/TESTING.md:109-120` — CI parity checks and installation fallback.
12. `SECURITY.md:3-6` — "research-grade simulator" and "Do not deploy... security boundary".
13. `assessment_logs/pytest.log:2-14` — pytest collection errors, missing `psutil`.
14. `assessment_logs/pytest.log:29-41` — missing `hypothesis` and `yaml` imports.
15. `assessment_logs/git_status_after.log:1-6` — changed files in this PR.

## Command Evidence
1. `cmd:git rev-parse --abbrev-ref HEAD > assessment_logs/git_branch.log`
   - `log:assessment_logs/git_branch.log`
   - `exit:0`
   - `timeout:30`
2. `cmd:git rev-parse HEAD > assessment_logs/git_sha.log`
   - `log:assessment_logs/git_sha.log`
   - `exit:0`
   - `timeout:30`
3. `cmd:git status --short > assessment_logs/git_status.log`
   - `log:assessment_logs/git_status.log`
   - `exit:0`
   - `timeout:30`
4. `cmd:uname -a > assessment_logs/platform.log`
   - `log:assessment_logs/platform.log`
   - `exit:0`
   - `timeout:30`
5. `cmd:pytest -q > assessment_logs/pytest.log 2>&1`
   - `log:assessment_logs/pytest.log`
   - `exit:2` (recorded in `assessment_logs/pytest.exit`)
   - `timeout:120`

## Git Evidence
- SHA: `d568a3929652f8ee758c92b9d1b48fcbe2d40e41`
- Branch: `work`
- Dirty status before edits: clean (`assessment_logs/git_status.log` empty)
- Dirty status after edits: 6 added paths (`assessment_logs/git_status_after.log`).
