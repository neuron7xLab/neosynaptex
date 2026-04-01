# M0 Bootstrap Foundation (canonical contract normalization)

M0 defines the machine-readable control plane for the canonical objective:

Clone → Run → See → Verify emergent dynamics.

This normalization pass aligns bootstrap naming to canonical proof vocabulary so later milestones can build without rename churn.

## Normalized controls

- `ci/statistical_power_config.json`
  - keeps avalanche admission as `planned` policy (future enforcement),
  - uses canonical admission keys: `N_min`, `duration_min_ms`, `bin_width_ms`, `min_avalanche_count`, `min_tail_count`, `p_value_threshold`, `ks_max`.
- `ci/validation_gates.json`
  - uses canonical gate IDs `G1`..`G8`,
  - uses canonical metric vocabulary (`rate_mean_hz`, `sigma_mean`),
  - points `G4_core_artifacts_complete` to canonical artifact contract: `emergence_plot.png`, `summary_metrics.json`, `criticality_report.json`, `avalanche_report.json`, `phase_space_report.json`, `run_manifest.json`.
- `schemas/proof-report.schema.json`
  - remains minimal and strict for bootstrap (`verdict`, numeric `verdict_code`, `gates`, `metrics`, `artifacts_verified`, `failure_reasons`).

## Honesty boundary at M0

The control plane is normalized and machine-readable, but full proof execution and all gate evaluators remain partially planned.
Only gates with evidence paths already present in the canonical artifact path are marked `wired`.
