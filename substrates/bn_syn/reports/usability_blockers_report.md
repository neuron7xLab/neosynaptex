# Practical Usability Blockers Report

## Audit scope
- Mode: evidence-bound usability blocker audit.
- Scope lock honored: only `reports/**` and `proof_bundle/**` artifacts added.
- Timestamp (UTC): 2026-02-16T12:38:03Z

## Intended use inference
**Inferred intended use:** BN-Syn is a deterministic Bio-AI research and validation platform where a new contributor should be able to install dependencies, run CLI workflows (demo/sleep-stack), and pass verification gates (tests, lint, typecheck, build).

**Evidence sources (>=2 met):**
1. `README.md` Start Here and canonical command block.
2. `docs/usage_workflows.md` golden-path workflows.
3. `pyproject.toml` CLI entrypoint (`bnsyn = bnsyn.cli:main`).
4. `.github/workflows/ci-pr-atomic.yml` quality/build jobs.

## Go/No-Go recommendation
**NO-GO** — P0 blockers prevent reliable verification/build completion from the documented contributor path.

## P0/P1 blockers

### BLK-001 (P0) — Verification gate fails due to stale proof bundle index hash
- **Category:** tests
- **Symptom:** `python -m pytest -m "not validation" -q` fails.
- **Expected:** Canonical test command exits 0.
- **Actual:** Fails at `tests/test_audit_suite_artifacts.py::test_proof_bundle_index_hashes_match_files` with SHA mismatch for `proof_bundle/command_index.json`.
- **Repro:**
  1) `python -m pip install -e ".[dev]"`
  2) `python -m pytest -m "not validation" -q`
- **Evidence:**
  - `cmd:python -m pytest -m "not validation" -q` | `log:proof_bundle/logs/04_verification.log` | `exit:1`
  - `cmd:python - <<"PY" ...` hash comparison | `log:proof_bundle/logs/05_post_test_state.log` | `exit:0`
  - `file:proof_bundle/index.json:3-6` snippet shows recorded SHA for `proof_bundle/command_index.json`
- **Minimal fix plan (analysis only):** regenerate `proof_bundle/index.json` with current hashes; enforce freshness in CI.

### BLK-002 (P0) — Build command unavailable after documented dev setup
- **Category:** build
- **Symptom:** `python -m build` fails after documented install command.
- **Expected:** Build should run from standard contributor environment setup.
- **Actual:** `No module named build` until installing `build` separately.
- **Repro:**
  1) `python -m pip install -e ".[dev]"`
  2) `python -m build`
- **Evidence:**
  - `cmd:python -m pip install -e ".[dev]"` | `log:proof_bundle/logs/03_new_user_path.log` | `exit:0`
  - `cmd:python -m build` | `log:proof_bundle/logs/04_verification.log` | `exit:1`
  - `cmd:python -m pip install build && python -m build` | `log:proof_bundle/logs/04_verification.log` | `exit:0`
  - `file:AGENTS.md:31-35` indicates build command expectation.
- **Minimal fix plan (analysis only):** add `build` to documented/dev setup path or include it in dev extras.

## Improvements (non-blocker)
- Repository becomes dirty after test run due to `tests_inventory.json` mutation (adds contributor friction and can confuse validation workflows).

## Fastest unblock sequence
1. Refresh stale proof bundle hash index and rerun canonical tests.
2. Align contributor setup so `python -m build` is available without manual extra install.
3. Re-run verification gates in order: tests → lint → typecheck → build.
