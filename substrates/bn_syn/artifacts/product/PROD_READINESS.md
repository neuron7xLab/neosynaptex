# Product Readiness Report

## Final Verdict
**FAIL**

## MVP Scope
- Install + execute CLI first-value path (`bnsyn demo`) with deterministic JSON output.
- Validate baseline through non-validation pytest gate.

## Gate Summary
| Gate | Severity | Status | Evidence |
|---|---|---|---|
| A | P0 | PASS | artifacts/product/evidence/screenshots_or_exports/happy_path.json |
| B | P0 | PASS | artifacts/product/PRD.md, artifacts/product/backlog.md |
| C | P1 | FAIL | artifacts/product/ux_review.md |
| D | P0 | FAIL | artifacts/product/evidence/logs/reliability_checks.log |
| E | P0 | PASS | artifacts/product/security_privacy_review.md |
| F | P1 | PASS | artifacts/product/metrics.md, artifacts/product/analytics_plan.md |
| G | P0 | PASS | artifacts/product/release_checklist.md, artifacts/product/launch_plan.md |
| H | P1 | PASS | artifacts/product/support_runbook.md |
| I | P1 | PASS | artifacts/product/PRD.md |
| J | P1 | PASS | artifacts/product/positioning.md |
| K | P0 | PASS | artifacts/product/compliance_notes.md |
| L | P1 | PASS | artifacts/product/launch_comms.md, artifacts/product/onboarding.md |

## Remaining Blockers (Minimal)
1. **P0 — Gate D fail**
   - Reproduction: `bnsyn demo --steps -1 --dt-ms 0.1 --seed 123 --N 16`
   - Root-cause hypothesis: CLI command path allows ValueError to surface as traceback without controlled failure UX.
   - Fix plan: add deterministic input validation + structured CLI error messaging at command boundary.
   - Evidence: `artifacts/product/evidence/logs/reliability_checks.log`.
2. **P1 — Gate C fail**
   - Reproduction: same command as above.
   - Root-cause hypothesis: missing error copy policy for invalid argument domain errors.
   - Fix plan: map validation/runtime argument errors to concise user-facing message and non-zero exit.
   - Evidence: `artifacts/product/ux_review.md`.

## PR Task Spec (for engineering agent)
PR_TITLE: Handle invalid `bnsyn demo` arguments with actionable CLI error output
GATE(S) UNBLOCKED: D, C
SEVERITY: P0
FILES: src/bnsyn/cli.py; tests/test_cli.py (or nearest CLI error-path test module)
CHANGESET (bullets, exact):
- Add command-boundary validation for `steps > 0`, `dt_ms > 0`, and `N > 0`.
- Convert current traceback-producing ValueError path into deterministic stderr message + non-zero exit code.
- Add tests: happy path unchanged; error path asserts user-facing message and exit code.
VALIDATION COMMANDS:
- python -m pytest -m "not validation" -q
- bnsyn demo --steps -1 --dt-ms 0.1 --seed 123 --N 16
- bnsyn demo --steps 120 --dt-ms 0.1 --seed 123 --N 32
EXPECTED EVIDENCE PATHS:
- artifacts/product/evidence/logs/reliability_checks.log
- artifacts/product/evidence/logs/baseline_checks.log
ROLLBACK PLAN:
- Revert CLI validation commit; restore previous behavior if regression introduced.
ACCEPTANCE CRITERIA:
- Invalid input produces actionable one-line error on stderr and non-zero exit without traceback.
- Valid demo path remains successful and deterministic.

## Launch Plan Summary
- Launch is blocked until Gate D is remediated and baseline re-run confirms PASS.
- Once remediated, run release checklist and regenerate scorecard/evidence bundle.
