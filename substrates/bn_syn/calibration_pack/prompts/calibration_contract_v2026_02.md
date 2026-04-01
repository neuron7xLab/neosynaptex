# Calibration Contract v2026.02

## Deterministic SHALL Statements

1. The agent SHALL emit all mandatory artifacts: `CALIBRATION_REPORT.json`, `CALIBRATION_SUMMARY.md`, and `calibration_pack/` subtrees.
2. Any non-zero score SHALL include at least one evidence pointer; if none exists, score resets to 0.
3. Outputs SHALL validate against JSON schemas in `calibration_pack/schemas/`.
4. Repeated runs on same SHA/toolchain SHALL produce identical fixture outputs and report JSON structure.
5. Sparse evidence SHALL apply pessimistic priors and reduce confidence.
6. Contradictions SHALL trigger deterministic downgrade and explicit rationale.
7. Termination SHALL require completeness >= 0.95 and evidence_density >= 0.80; otherwise partial status MUST be declared.

## Confidence Model

- `unknown_ratio = unknown_criteria / max(total_criteria, 1)`
- `evidence_strength_index` is integer in `[1,5]`.
- `confidence = clip(1 - 0.6*unknown_ratio - 0.15*(5-evidence_strength_index)/4 - 0.25*contradiction_flag, 0, 1)`
- `adjusted_risk = risk_score * confidence`

## Bayesian Prior Adjustment

- Prior risk per module defaults to pessimistic baseline `0.70`.
- Posterior update uses evidence pressure: `posterior_risk = prior*(1-evidence_factor) + observed_risk*evidence_factor`.
- `evidence_factor = min(1.0, evidence_items / max(total_criteria,1))`.

## Contradiction Rules

- Rule C1: `authz_strong=true` with `tenant_leak=true` => contradiction.
- Rule C2: `sbom_complete=true` with `runtime_dep_gap=true` => contradiction.
- Rule C3: `observability_ok=true` with `no_failure_plan=true` => contradiction.
