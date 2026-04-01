# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Changed
- `ci/validation_gates.json`: schema_version 1.3.0 → 1.4.0. G9 threshold restructured to per-metric policy objects with explicit `tolerance`, `policy`, and `policy_by_source` fields. Added `recompute_policy` block with canonical raw artifact path, fallback strategy, and `manifest_steps_validation` guard.
- `schemas/proof-report.schema.json`: schema_version const pinned to `1.1.0`. `recompute_sources` and `metric_consistency` fields hardened from `additionalProperties: true` to fully typed closed schemas with enum-validated `spike_events_source`.
- `src/bnsyn/proof/evaluate.py`: Refactored spike-events recomputation pipeline. `recompute_metrics_from_artifacts` now reads policy exclusively from the G9 registry gate. Canonical raw artifact path is `traces.npz` only (no glob fallback). Malformed canonical raw fails closed without rate-trace fallback. `_manifest_float` replaced with `_extract_manifest_numeric` (manifest-only, no summary fallback). `evaluate_gate_g9_metric_consistency` is registry-driven. `_fail_closed_report` emits fully schema-valid `recompute_sources` and `metric_consistency`.
- `PROOF_SCHEMA_VERSION` constant: `1.0.0` → `1.1.0`.

## [0.5.0] - 2026-03-18

### Added
- Canonical proof CI spine with phase-space gating, agent feedback, remediation synthesis, cross-commit analytics, and OIDC attestation for `canonical_run_bundle.tgz`.
- Deterministic `scripts/bootstrap.sh` environment bootstrap path and fail-safe Docker entrypoint bound to `make quickstart-smoke`.
- Cryptographic linkage between `emergence_plot.png` and `population_rate_trace.npy` in `product_summary.json` and the human-facing `index.html`.

### Changed
- Branch-protection governance and required status context metadata now include `canonical-proof-spine`, `cross-commit-analytics`, and `attest-canonical-bundle` as merge-blocking checks.
- Project version advanced from `0.2.0` to `0.5.0` to mark the singular canonical proof orchestration milestone.

## [0.2.0] - 2026-02-06

### Added
- Formal CODEBASE_READINESS rubric and maturity mapping.
- Semver-aware API contract gate tooling.
- Deterministic quickstart contract and integration examples.
- Release pipeline workflow with dry-run publish stage.
