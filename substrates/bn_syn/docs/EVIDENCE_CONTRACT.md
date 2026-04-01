# AOC v1.0 Evidence Contract

Required files per run:

- `final_artifact.md`
- `zeropoint.json`
- `run_summary.json`
- `sigma_trace.json`
- `delta_trace.json`
- `audit_trace.json`
- `auditor_reliability_trace.json`
- `termination_verdict.json`
- `evidence_bundle/`

Verifier basis requirements:

- `audit_trace.json` must record the two-stage audit flow for each iteration:
  - `primary_audit`
  - `verification`
- `auditor_reliability_trace.json` must include:
  - top-level `verification_status`
  - top-level `metrics_status`
  - `verified_record_count`
  - `unverified_record_count`
  - per-record `verification_status`
  - per-record `verifier_basis`
- `verifier_basis` for verified records must include a reproducible basis descriptor, including provider identity and content/task binding (for example, `provider`, `basis_version`, `task_id`, and content hash).
- A run may only claim `audit_reliability_status = "reliable_audit"` when a verifier basis is present for the terminal audit verdict.

`termination_verdict.json` fields:
- `status`
- `stop_reason`
- `iteration`
- `delta`
- `sigma_distance`
- `audit_passed`
- `audit_reliability_status`
- `band.min_delta`
- `band.max_delta`
