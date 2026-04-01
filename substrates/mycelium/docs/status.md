# System Status

Last verified: 2026-03-24

## Verification Summary

| Check | Status | Command |
|-------|--------|---------|
| Local reproduce | **PASS** | `uv run python experiments/reproduce.py` |
| Local adversarial | **PASS** (6/6) | `uv run python experiments/adversarial.py` |
| Local tests | **PASS** (1944) | `bash ci.sh` gate 3 |
| Lint | **PASS** | `ruff check` |
| Types | **PASS** (15 files, --strict) | `mypy --strict` |
| Import contracts | **PASS** (8/8) | `lint-imports` |
| Full local CI | **PASS** (6/6 gates) | `bash ci.sh` |
| GitHub Actions ready | **YES** (ci.yml updated with verify job) | See below |
| Blocked by repo settings | **POSSIBLE** | See unblock steps |

## GitHub Actions

The `ci.yml` workflow includes a `verify` job that:
1. Installs with `--extra bio`
2. Runs `experiments/reproduce.py` (canonical reproduction)
3. Runs `experiments/adversarial.py` (invariant validation)
4. Uploads results as artifacts

### If Actions are blocked

Go to: **Settings → Actions → General**

1. Set "Actions permissions" to "Allow all actions and reusable workflows"
2. Under "Workflow permissions", select "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests" (if needed)
4. Click Save
5. Re-run the workflow

## Known Limitations

1. Tests requiring `fastapi`/`pandas` skip without `[api]`/`[data]` extras (~200 tests)
2. Benchmark gates are hardware-dependent (use `uv run python benchmarks/calibrate_bio.py` to recalibrate)
3. TDA persistent homology returns zero features for low-contrast Turing fields (documented behavior, not a bug)
4. DiagnosticMemory learned rules depend on observation sequence (non-deterministic by design)
