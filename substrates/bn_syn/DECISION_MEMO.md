# DECISION_MEMO

## Decision Context
Current branch belongs to BN-Syn simulator, while requested consulting frame references Prompt Lab X SaaS. Decision needed: how to unblock PR safely without pretending nonexistent surfaces exist.

## Option A — Minimal Change (Fastest)
- Deliver evidence-backed assessment docs for BN-Syn only.
- Cost: Low (hours)
- Risk reduction: Medium (clarifies reality, blocks unsafe assumptions)
- Timeline: Same PR
- Rollback: revert docs commit
- Unknowns: SaaS target architecture remains unresolved

## Option B — Medium Hardening (Balanced)
- Option A + dependency-complete local environment + full test/quality run with archived artifacts.
- Cost: Medium (0.5–1 day)
- Risk reduction: High for merge confidence
- Timeline: next commit cycle
- Rollback: revert environment/bootstrap changes
- Unknowns: still no SaaS code evidence

## Option C — Strategic Refactor (Long-term ROI)
- Create explicit target-state architecture package for Prompt Lab X and a gap-closure roadmap from BN-Syn patterns (if intentional reuse).
- Cost: High (multi-sprint)
- Risk reduction: Highest for strategic alignment
- Timeline: 2–6 weeks
- Rollback: ADR-based phased delivery
- Unknowns: product scope ownership and platform constraints

## Recommendation
**Recommend Option B now**, then C only if BN-Syn is intended as seed for Prompt Lab X.
Rationale: fastest path to verifiable merge confidence while preventing category errors.

## Rollout / Rollback / Migration Safety
- Rollout: merge docs + guards, then run full dependency-complete CI parity checks.
- Rollback: single commit revert (no runtime state change).
- Migration safety: N/A for this PR (no DB/schema/runtime code changes).

## Non-Negotiable Safeguards
1. No ship-to-main without dependency-complete tests passing.
2. No architecture claims without file/command evidence.
3. Preserve explicit “not a security boundary” warning until production hardening is complete.
4. Track unknowns as blocking decision items, not assumptions.
