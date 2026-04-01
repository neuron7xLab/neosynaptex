# Metrics Definition

## North Star
- Activation to first value in one session.
- Counting rule: successful execution of `bnsyn demo` returning parseable JSON with top-level `demo` object.

## Supporting KPIs
1. Happy-path success rate (build+demo command success / attempts).
2. Test-gate pass rate (`pytest -m "not validation"`).
3. Reliability loop success rate across 3 repeated demo runs.

## Cohorts
- New local user setup attempts.
- Repeat deterministic validation runs.

## Exclusions
- Validation/performance long-run suites excluded from MVP activation KPI.
- Non-CLI surfaces excluded.

## Current state
- Instrumentation implementation: **LOG-DERIVED ONLY** (no explicit event bus).
