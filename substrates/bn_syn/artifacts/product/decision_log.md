# Decision Log

## 2026-02-18 — Use fail-closed launch verdict
- Decision: Mark readiness FAIL until open P0 blockers are remediated.
- Alternatives: Soft-launch with known traceback behavior.
- Rationale: Deterministic gate policy requires reliable, actionable error behavior.
- Evidence: `artifacts/product/evidence/logs/reliability_checks.log`.
- Rollback note: Update verdict after P0 fixes and full baseline rerun.

## 2026-02-18 — Define MVP as CLI first-value flow
- Decision: Scope MVP to install + `bnsyn demo` first-value output.
- Alternatives: Include all benchmark/validation workflows in MVP gate.
- Rationale: Smallest viable launch objective consistent with README quickstart.
- Evidence: `README.md`, `artifacts/product/evidence/logs/baseline_build_run.log`.
- Rollback note: Expand scope only with explicit product requirement change.
