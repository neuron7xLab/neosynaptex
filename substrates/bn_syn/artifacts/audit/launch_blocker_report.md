## LAUNCH BLOCKER REPORT

**RESULT:** PASS
**Repo Root:** /workspace/bnsyn-phase-controlled-emergent-dynamics
**Audit Timestamp (UTC):** 2026-02-17T18:29:11Z
**Python:** 3.12.12
**Pip:** 25.3 (host), 26.0.1 (audit venv)

### Scorecard

| Axis | Weight | Score (0/3/6/8/10) | Evidence (command/path) |
|---|---:|---:|---|
| Installability | 20% | 10/10 | `artifacts/audit/.venv/bin/python -m pip install -e .` and `-e .[test]` succeeded (`artifacts/audit/logs/04_installability.log`). |
| Quickstart UX | 15% | 8/10 | `python -m bnsyn --help` and `bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32` produced deterministic JSON in 1s (`artifacts/audit/demo.json`, `artifacts/audit/logs/05_quickstart.log`). |
| Test Integrity | 20% | 10/10 | `pytest --collect-only -q` succeeded; `make test-gate` completed with progress markers in 46s (`artifacts/audit/logs/06_tests.log`). |
| Build/Packaging | 15% | 10/10 | `python -m build` and wheel install/import succeeded (`artifacts/audit/logs/07_build.log`). |
| Docs Truthfulness | 10% | 6/10 | README quickstart commands validated (`make quickstart-smoke`); `make docs` failed due missing `sphinx` (`artifacts/audit/logs/08_docs.log`). |
| CI Truthfulness | 10% | 8/10 | Canonical PR workflow (`ci-pr-atomic.yml`) includes collect-only + `make test-gate` and explicit permissions (`artifacts/audit/logs/10_ci.log`, `.github/workflows/ci-pr-atomic.yml`). |
| Security Hygiene | 10% | 3/10 | Declared `make security` fails locally because `gitleaks` missing (`artifacts/audit/logs/09_security.log`). |

**Weighted Total:** 84/100 — ADVANCED

### Blockers (Exhaustive, Prioritized)

| Priority | Blocker | Symptom (1 line) | Impact (1 line) | Minimal Fix Direction (1 line) | Proof (exact cmd output or path) |
|---|---|---|---|---|---|
| P2 | Docs build path not self-contained in audit env | `make docs` fails with `No module named sphinx`. | Docs build cannot be verified from fresh runtime/test install alone. | Add docs extra (e.g., `.[docs]`) and wire `make docs` to documented dependency set. | `artifacts/audit/logs/08_docs.log` (`python -m sphinx -b html docs docs/_build/html` -> error). |
| P2 | Security target requires undeclared local binary | `make security` fails with `gitleaks: No such file or directory`. | Security hygiene command is not reproducible for a new user without extra setup knowledge. | Declare/install `gitleaks` in reproducible tooling path (pipx/container/script) and document it. | `artifacts/audit/logs/09_security.log`. |

### Canonical Commands (Verbatim)

- RUNTIME_INSTALL: `python -m pip install -e .`
- TEST_INSTALL: `python -m pip install -e ".[test]"`
- QUICKSTART: `bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32`
- COLLECT_ONLY: `python -m pytest --collect-only -q`
- GATE: `make test-gate`
- BUILD_WHEEL: `python -m build`
- INSTALL_WHEEL: `python -m pip install dist/bnsyn-0.2.0-py3-none-any.whl`

### Commands Executed (In Order)

- `python -V` => 0
- `python -m pip --version` => 0
- `python -c "import sys; print('OK')"` => 0
- `python -c "print(1+1)"` => 0
- `python -m pip check` => 0 (NON-BLOCKING)
- `python -m venv artifacts/audit/.venv` => 0
- `artifacts/audit/.venv/bin/python -m pip install --upgrade pip` => 0
- `artifacts/audit/.venv/bin/python -m pip install -e .` => 0
- `artifacts/audit/.venv/bin/python -m pip install -e ".[test]"` => 0
- `artifacts/audit/.venv/bin/python -m bnsyn --help` => 0
- `artifacts/audit/.venv/bin/bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32 > artifacts/audit/demo.json` => 0
- `artifacts/audit/.venv/bin/python -m pytest --version` => 0
- `artifacts/audit/.venv/bin/python -m pytest --markers` => 0
- `artifacts/audit/.venv/bin/python -m pytest --collect-only -q` => 0
- `timeout 600 bash -lc "source artifacts/audit/.venv/bin/activate && make test-gate"` => 0
- `artifacts/audit/.venv/bin/python -m pytest -m smoke -q` => 0 (NON-BLOCKING)
- `artifacts/audit/.venv/bin/python -m pip install build` => 0
- `artifacts/audit/.venv/bin/python -m build` => 0
- `python -m venv artifacts/audit/.venv-wheel` => 0
- `artifacts/audit/.venv-wheel/bin/python -m pip install dist/bnsyn-0.2.0-py3-none-any.whl` => 0
- `artifacts/audit/.venv-wheel/bin/python -c "import bnsyn; print(getattr(bnsyn,'__version__','<no version>'))"` => 0
- `bash -lc "source artifacts/audit/.venv/bin/activate && make quickstart-smoke"` => 0
- `bash -lc "source artifacts/audit/.venv/bin/activate && make docs"` => 2 (NON-BLOCKING)
- `bash -lc "source artifacts/audit/.venv/bin/activate && make security"` => 2 (NON-BLOCKING)
- `rg -n "pull_request:|permissions:|pytest --collect-only|make test-gate" ...` => 0

### Audit Artifacts Written (gitignored)

- artifacts/audit/pip-freeze.pre.txt
- artifacts/audit/pip-freeze.post.txt
- artifacts/audit/demo.json
- artifacts/audit/logs/*.log

### Next PR (Single Highest-Leverage Objective)

**PR Objective (one sentence):** Make docs/security flows reproducible from a fresh clone by codifying dependencies/tool bootstrap for `make docs` and `make security`.
**Acceptance (binary):**
- [ ] `python -m pip install -e ".[test,docs]" && make docs` exits 0 in a clean venv.
- [ ] `make security` exits 0 in a clean venv/container without manual binary installs.
**Touched Paths (allowlist):** `pyproject.toml`, `Makefile`, `README.md`, `docs/TESTING.md`.

END.
