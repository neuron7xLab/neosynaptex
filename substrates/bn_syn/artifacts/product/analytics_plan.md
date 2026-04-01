# Analytics Plan

## Event Taxonomy (Spec)
- `activation.attempt`
  - Trigger: immediately before `bnsyn demo` execution.
  - Properties: `request_id`(future), `steps`, `dt_ms`, `seed`, `N`.
- `activation.success`
  - Trigger: JSON output includes `demo`.
  - Properties: output summary metrics.
- `activation.failure`
  - Trigger: exception/non-zero exit.
  - Properties: error class/message fragment.

## Funnel
1. install.success
2. cli.help.success
3. demo.run
4. demo.success (first value)

## Insertion points (future implementation)
- `src/bnsyn/cli.py` in `_cmd_demo` before and after `run_simulation`.
- exception handling block in CLI dispatcher.

## Evidence
- Current proxy evidence is command logs in `artifacts/product/evidence/logs/`.
