# Quality Surface Map

| Category | Surface | PR Trigger | Blocking | Runtime Budget | Flake Risk |
|---|---|---|---|---|---|
| C1 Correctness | `pytest` core suite via `ci-pr-atomic` | yes | yes | 12m budget for no-escape contract job | low |
| C2 Regression | entropy gate tests, benchmark regression tests | yes | yes | inherited pytest budget | medium |
| C3 Determinism | `determinism` job + `scripts.verify_reproducible_artifacts` | yes | yes | 20m determinism + 12m contracts | low |
| C4 Data/schema integrity | `tests/test_schema_contracts.py`, manifest + inventory tests | yes | yes | included in contracts job | low |
| C5 Supply-chain integrity | `tests/test_actions_pinning.py`, pinned actions in workflows | yes | yes | included in contracts job | low |
| C6 Security linting | `bandit -r src/bnsyn` evidence run | manual evidence | blocked if unknown | n/a | medium |
| C7 Mutation/fault injection | mutation pipeline script/tests | schedule/manual | non-blocking | long-running | medium |
| C8 Workflow integrity | `tests/test_validate_workflow_contracts.py`, workflow-integrity workflow | yes | yes | separate workflow budget | low |
| C9 Evidence integrity | reproducibility report + sha256 manifest in `evidence/zqsg_2026_02_12` | yes (contracts) | yes | included in contracts job | low |
