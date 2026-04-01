# RISK_REGISTER

| risk_id | description | surface | likelihood | impact | confidence | evidence | mitigation | owner | ETA |
|---|---|---|---|---|---|---|---|---|---|
| R-001 | Full test suite cannot be executed in current env due missing deps (`yaml`,`hypothesis`,`psutil`), reducing release confidence. | Delivery/Correctness | High | High | High | `assessment_logs/pytest.log` | Install `.[test]`/`.[dev]`, rerun smoke+full pytest, archive logs in CI artifacts. | DevEx | 0.5 day |
| R-002 | Product requirement mismatch: requested Prompt Lab X SaaS architecture is not present in this repo. | Architecture/Governance | High | High | High | `README.md`, `pyproject.toml` | Re-baseline scope: either assess BN-Syn only or provide target-state gap plan to Prompt Lab X. | Tech Lead | 1 day |
| R-003 | Security boundary misuse risk: docs warn not to deploy as security boundary. | Security | Medium | High | High | `SECURITY.md` | Add explicit deployment policy checks and release checklist guardrail in CI/docs. | Security | 1 day |
| R-004 | CI/test-tier complexity can create gate misconfiguration or false confidence if workflows drift. | Reliability/Delivery | Medium | Medium | Medium | `docs/CI_GATES.md` | Add periodic workflow contract validation + required status context sync audit. | Platform | 2 days |
| R-005 | Determinism/provenance invariants may regress without strict enforcement in every path. | Correctness/Reliability | Medium | Medium | Medium | `docs/ARCHITECTURE_INVARIANTS.md` | Expand invariant-focused tests on manifest + seed determinism in critical scripts. | Core Maintainers | 2 days |

## Ship Gate
**GO-WITH-GUARDS**
- Guard 1: dependency-complete test run required before merge to main.
- Guard 2: scope alignment decision required (BN-Syn vs Prompt Lab X target architecture).
- Guard 3: explicit non-production security-boundary warning retained in release notes/checklists.

## UNKNOWNs (fail-closed)
1. UNKNOWN: auth/authz model for intended SaaS platform (resolve via target repo/spec).
2. UNKNOWN: migration/rollback constraints for production datastore (resolve via infra docs).
3. UNKNOWN: deploy pipeline and secrets handling posture for production target (resolve via CI/CD + secrets inventory).
4. UNKNOWN: uptime/SLO and incident response commitments (resolve via ops policy docs).
