# DOPA-AF7 Release Gate

Status: executable fail-closed gate, not a theory verdict.

The gate converts the dopamine mechanism from a narrative construct into a release
contract. It does not pass because dopamine-shaped code exists. It passes only
when the mechanism demonstrates budgeted verified-closure advantage under
independent evidence.

## Seven required tasks

1. `construct_freeze_gate` — executable DNCA signal and signed vRPE field exist.
2. `calibrated_vrpe_estimator` — the value estimator is calibrated and B2 truth-correlation is robust.
3. `verified_closure_corpus` — verifier beats majority/random and VCR is not accuracy collapse.
4. `budgeted_routing_integration` — dopa signal drives the budget router, not a disconnected benchmark.
5. `hard_negative_control_battery` — sign flip, random, no-vRPE, uncertainty, permutation and overactivation controls are enforced.
6. `statistical_causality_harness` — dopa produces preregistered closure-yield advantage (`delta >= 0.05`, `p < 0.01`).
7. `release_grade_evidence_capsule` — config/data/repro hashes bind the verdict.

## Command

```bash
python scripts/dopa_af7_release_gate.py
```

For release CI after the estimator/corpus/router are implemented:

```bash
python scripts/dopa_af7_release_gate.py --require-ready
```

## Current expected verdict

`AF7_INADMISSIBLE` is currently the correct outcome because the existing
`dopa_validity_001_result.json` records an uncalibrated value estimator and a
non-robust B2 truth-correlation gate. This is a blocker, not a defect in the gate.
The gate prevents any future PR from presenting this state as Academy-Fellow-ready.
