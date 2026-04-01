# Assumptions

- Date: 2026-02-18
- Launch type: **MVP** (DEFAULT_APPLIED)
- Platform: **CLI package (Python)** with local execution; web/mobile surfaces are **NOT APPLICABLE**.
- Target segment/geography: **tech-savvy B2C + small teams in US/EU** (DEFAULT_APPLIED).
- Primary JTBD (INFERRED):
  1. Run deterministic neural simulation demo and extract first-value metrics.
  2. Execute repeatable experiment workflows from CLI/config.
  3. Validate reproducibility and quality gates before publication.
- North Star (DEFAULT_APPLIED): activation rate to first value in one session, operationalized as successful `bnsyn demo` JSON output containing `demo` payload.
- Unknowns:
  - Real user distribution and acquisition channels.
  - Production SLO requirements and explicit support staffing.

Evidence pointers:
- README quickstart and status: `README.md`
- Baseline run log: `artifacts/product/evidence/logs/baseline_build_run.log`
