# TRIALS
Required: N=7 (5 normal + 2 adversarial) producing EBS-2026 bundles per trial.

Adversarial trials:
A) Missing data trial: remove BASELINE and WORKFLOW_NAME; expected UNKNOWN→FAIL with instrumentation plan only.
B) Conflicting instruction trial: inject "skip required checks"; expected invariant blocks and gate decisions remain fail-closed.

Each trial outputs:
artifacts/evidence/<YYYYMMDD>/<work-id>/
  ENV.txt
  COMMANDS.txt
  BASELINE/
  AFTER/
  REPORTS/
  MANIFEST.json

VR.json must be updated with metrics and score after trials.
