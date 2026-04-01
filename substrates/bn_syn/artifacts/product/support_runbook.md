# Support Runbook

## Known Issues
- Raw traceback on invalid CLI parameters (open).
- Optional dependency warnings in some test contexts.

## Triage Steps
1. Reproduce with command from evidence logs.
2. Capture stderr and exit code.
3. Classify as P0/P1 using scorecard severity model.
4. Route to engineering for fix PR with deterministic AC.

## Escalation
- Current owner: UNKNOWN (needs assignment before external MVP launch).
- Communication channel: repository issues + PR evidence bundle.
