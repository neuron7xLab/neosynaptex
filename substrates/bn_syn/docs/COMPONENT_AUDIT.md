# Component Audit Table

| Component | SPEC section | Status (VERIFIED/UNVERIFIED/DEPRECATED) | Implementation paths | Test paths | Claim IDs | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| P0-1 | P0-1 | VERIFIED | src/bnsyn/neuron/adex.py; src/bnsyn/sim/network.py | tests/test_adex_smoke.py; tests/validation/test_adex_validation.py | CLM-0001, CLM-0002 | AdEx equations, reset rule, and exp clamp aligned with spec. |
| P0-2 | P0-2 | VERIFIED | src/bnsyn/synapse/conductance.py; src/bnsyn/sim/network.py | tests/test_synapse_smoke.py; tests/validation/test_synapse_validation.py | CLM-0003 | Mg block and conductance decay align with spec equations. |
| P0-3 | P0-3 | VERIFIED | src/bnsyn/plasticity/three_factor.py | tests/test_plasticity_smoke.py; tests/validation/test_plasticity_validation.py | CLM-0004, CLM-0005 | Eligibility × neuromodulator update and weight bounds verified. |
| P0-4 | P0-4 | VERIFIED | src/bnsyn/criticality/branching.py; src/bnsyn/criticality/analysis.py | tests/test_criticality_smoke.py; tests/validation/test_criticality_validation.py | CLM-0006, CLM-0007, CLM-0008, CLM-0009 | σ estimation and gain homeostasis validated. |
| P1-5 | P1-5 | VERIFIED | src/bnsyn/temperature/schedule.py | tests/test_temperature_smoke.py; tests/validation/test_temperature_validation.py | CLM-0019 | Geometric cooling and gate sigmoid covered. |
| P1-6 | P1-6 | VERIFIED | src/bnsyn/consolidation/dual_weight.py | tests/test_consolidation_smoke.py; tests/validation/test_consolidation_validation.py | CLM-0010, CLM-0020 | Dual-weight dynamics and tagging/protein gating verified. |
| P1-7 | P1-7 | VERIFIED | src/bnsyn/energy/regularization.py | tests/test_energy_smoke.py; tests/validation/test_energy_validation.py | CLM-0021 | Energy regularization objective terms verified. |
| P2-8 | P2-8 | VERIFIED | src/bnsyn/numerics/integrators.py | tests/test_dt_invariance.py; tests/validation/test_numerics_validation.py | CLM-0022 | Euler/RK2 and exp decay methods covered. |
| P2-9 | P2-9 | VERIFIED | src/bnsyn/rng.py; src/bnsyn/sim/network.py | tests/test_determinism.py; tests/validation/test_determinism_validation.py | CLM-0023 | Determinism protocol and explicit RNG injection enforced. |
| P2-10 | P2-10 | VERIFIED | src/bnsyn/calibration/fit.py | tests/test_calibration_smoke.py; tests/validation/test_calibration_validation.py | CLM-0024 | Deterministic least-squares fit validated. |
| P2-11 | P2-11 | VERIFIED | src/bnsyn/sim/network.py | tests/test_network_smoke.py; tests/validation/test_network_validation.py | CLM-0025 | Reference simulator with safety bounds verified. |
| P2-12 | P2-12 | VERIFIED | src/bnsyn/cli.py | tests/test_cli_smoke.py; tests/validation/test_cli_validation.py | CLM-0026 | CLI bench harness outputs deterministic metrics. |
