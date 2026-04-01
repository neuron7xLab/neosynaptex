# User Journeys (Top 3)

## Journey 1 — First Value (Primary Happy Path)
1. Install package (`python -m pip install -e ".[test]"`).
2. Run `bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32`.
3. Receive JSON payload with `demo` metrics (`rate_mean_hz`, `sigma_mean`, etc.).
4. Interpret as first-value simulation signal.

## Journey 2 — Sleep Stack Exploration
1. Run `bnsyn sleep-stack --help` then `bnsyn sleep-stack ... --out <dir>`.
2. Inspect produced outputs under selected artifact directory.

## Journey 3 — Validation/Readiness Loop
1. Execute non-validation tests (`python -m pytest -m "not validation" -q`).
2. Run quality and release checks via Makefile targets.
3. Review evidence artifacts and reports.

Evidence:
- `artifacts/product/evidence/logs/baseline_build_run.log`
- `artifacts/product/evidence/screenshots_or_exports/happy_path.json`
- `artifacts/product/evidence/logs/baseline_checks.log`
