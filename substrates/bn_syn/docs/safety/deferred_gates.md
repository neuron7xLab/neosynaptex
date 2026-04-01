# Safety Gates Status

| gate_id | tool | where it runs | status | reproduction command | owner | follow-up link |
| --- | --- | --- | --- | --- | --- | --- |
| SAFETY-ARTIFACTS | `tools/safety/check_safety_artifacts.py` | `.github/workflows/workflow-integrity.yml` | enforced | `python tools/safety/check_safety_artifacts.py` | Safety Engineering | N/A |
| WORKFLOW-ACTIONLINT | `actionlint` + `shellcheck` | `.github/workflows/workflow-integrity.yml` | enforced | `actionlint -verbose` | Release Engineering | N/A |
