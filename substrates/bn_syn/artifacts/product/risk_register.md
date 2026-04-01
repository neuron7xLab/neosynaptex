# Risk Register

| Risk | Impact | Likelihood | Detection | Mitigation | Owner | Status | Evidence |
|---|---|---|---|---|---|---|---|
| Invalid CLI input raises raw traceback, harming UX predictability | High | Medium | Reliability negative-path check | Add explicit input validation and graceful CLI error mapping | Eng | Open (P0) | artifacts/product/evidence/logs/reliability_checks.log |
| No explicit analytics event emission | Medium | High | Analytics plan review | Implement activation event logging schema in CLI | PM+Eng | Open (P1) | artifacts/product/analytics_plan.md |
| Legal/compliance posture implicit only | Medium | Low | Compliance gate review | Create explicit privacy/terms note when distribution changes | PM | Open (P1) | artifacts/product/compliance_notes.md |
| Support runbook lacks named escalation channel | Medium | Medium | Supportability review | Add owner/on-call contact model before external launch | PM | Open (P1) | artifacts/product/support_runbook.md |
