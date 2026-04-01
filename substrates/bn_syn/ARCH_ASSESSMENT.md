# ARCH_ASSESSMENT

## Mode Selection
- Executed **M1 Rapid Architecture Assessment** first.
- Branched into **M2-lite due diligence** because verification and security signals indicated deployment-risk unknowns.

## STEP 0 — Intake & Objective Lock
- **PR goal (this engagement):** produce board-level, implementable technical assessment artifacts to unblock PR decisioning.
- **User-visible changes:** documentation/reporting only.
- **Systems touched:** repository-level assessment docs + evidence logs.
- **Rollout risk:** low for runtime behavior (no simulator logic changes), medium for decision quality if evidence is weak.
- **Success criteria (this PR):**
  1) Mandatory six artifacts produced.
  2) Every material claim tied to evidence or labeled ASSUMPTION/UNKNOWN.
  3) Ship gate + next-step execution plan provided.
- **Time budget (best effort):** 60% evidence capture + verification, 40% decision artifacts.

## STEP 1 — Repo & PR Evidence Capture
- **Repo identity:** branch `work`, SHA captured in `assessment_logs/git_sha.log`.
- **Tech stack observed:** Python 3.11+ package (`pyproject.toml`), pytest/hypothesis/ruff/mypy quality toolchain.
- **Boundaries found:** deterministic simulator core (`src/bnsyn/*`), experiments, benchmarks, docs/spec/governance, CI gates.
- **Diff scan:** this PR adds assessment markdown outputs and logs only (no core code/migration changes).
- **Verification executed:** `pytest -q` failed at collection due missing deps (`yaml`, `hypothesis`, `psutil`).

## Current Architecture Sketch (as-is)
1. **Spec/Governance plane**: SPEC + claims/evidence as normative source.
2. **Simulation plane**: AdEx neuron/synapse/criticality/temperature modules.
3. **Validation plane**: testing tiers (blocking smoke, scheduled validation/property/chaos, benchmark tier).
4. **Operational plane**: GitHub workflows, quality gates, security scans.

### Trust boundaries
- Local/dev runtime vs CI verification.
- Generated artifacts/results vs normative docs.
- Research simulator boundary: explicitly not a production security boundary.

## Critical Paths & Invariants
- Critical paths in repo: experiment execution, sleep-stack demo, claims-validation CI, benchmark regression.
- Invariants: strict array shape/dtype/finiteness validation; deterministic seed/provenance capture; schema and sleep-cycle guardrails.

## Key Constraints
- **Constraint:** repository is BN-Syn research simulator, not Prompt Lab X SaaS monorepo.
- **Constraint:** security document states non-production security-boundary status.
- **Constraint:** local environment lacks test deps; full confidence blocked until dependency-complete run.

## Top 5 Architectural Risks (blast-radius prioritized)
1. **Verification blind spot:** inability to run full test suite locally can hide regressions.
2. **Context mismatch risk:** requested SaaS controls (authz/billing/tenant) absent in current codebase.
3. **Security boundary ambiguity:** teams may over-interpret research code for production use.
4. **Operational drift:** CI-tier complexity increases chance of misconfigured gate bypass.
5. **Performance regression detection lag:** weekly benchmark cadence may miss short-lived regressions.

## ASSUMPTIONS / UNKNOWNS
- UNKNOWN: deployment target and runtime SLOs for any productionized derivative.
- UNKNOWN: explicit rollback strategy for simulator data/artifact schema evolution.
- ASSUMPTION: PR reference is current branch tip (`work`).
