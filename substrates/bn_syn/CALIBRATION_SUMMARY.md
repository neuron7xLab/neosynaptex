# Calibration Summary

## Operational Readiness
Status: PROVISIONAL / NOT INDEPENDENTLY VALIDATED

The calibration harness currently passes deterministic fixture checks and schema validation, but it is not independently validated against production telemetry.

## Top 5 Blockers
1. Synthetic fixtures still proxy real telemetry.
2. `jsonschema` CLI emits deprecation warning.
3. Calibration gates are not yet CI-enforced across every workflow.
4. Priors are global, not module-specific.
5. Prompt-Lab TypeScript constraints are external to this Python repo.

## Replay Commands
`python calibration_pack/harness/run_calibration.py`
`python calibration_pack/harness/build_report.py`
`python -m jsonschema -i CALIBRATION_REPORT.json calibration_pack/schemas/calibration_report.schema.json`
`python calibration_pack/harness/validate_summary.py`
