# EXECUTION_PLAN

## Sequenced Task Plan
1. **Scope lock (critical path)**
   - Confirm whether PR scope is BN-Syn-only or cross-repo Prompt Lab X architecture advisory.
   - Outcome: signed scope note in PR body.
2. **Environment parity restore (critical path)**
   - Install test deps (`python -m pip install -e ".[test]"`).
   - Re-run pytest smoke/full and capture logs.
   - Outcome: green (or actionable failures) with artifacts.
3. **Risk guard implementation**
   - Add/confirm release checklist item for non-security-boundary status.
   - Validate required CI contexts and workflow contracts.
   - Outcome: reduced accidental misuse risk.
4. **Confidence uplift pass**
   - Recompute ship gate with updated evidence.
   - Outcome: GO or GO-WITH-GUARDS decision refresh.

## Parallelizable Workstreams
- A: test environment repair + verification.
- B: scope/decision alignment with stakeholders.
- C: docs/governance guardrail updates.

## Effort Buckets
- Scope lock: S (≤2h)
- Env parity + test rerun: M (0.5 day)
- Guardrails and decision refresh: S–M (2–4h)

## Verification Plan (commands)
1. `python -m pip install -e ".[test]"`
2. `python -m pytest -m "not validation" -q`
3. `python -m pytest -q`
4. `ruff check .`
5. `python -m scripts.validate_workflow_contracts`

## Definition of Done — This PR
- Six mandatory assessment artifacts committed.
- Evidence index maps every material claim.
- Ship gate declared with confidence and blockers.

## Definition of Done — Next Milestone
- Dependency-complete CI parity suite passes.
- Scope mismatch resolved with ADR/decision log.
- Unknowns converted to owners + dated tasks.
