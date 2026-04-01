# Evidence Coverage

| Claim ID | Tier | Normative | Status | Bibkey | DOI/URL | Spec Section | Implementation Paths | Verification Paths |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLM-0001 | Tier-A | true | PROVEN | brette2005adaptive | 10.1152/jn.00686.2005 | P0-1 AdEx neuron model | `src/bnsyn/neuron/adex.py`, `src/bnsyn/sim/network.py` | `tests/test_adex_smoke.py`, `tests/test_network_smoke.py` |
| CLM-0002 | Tier-A | true | PROVEN | brette2005adaptive | 10.1152/jn.00686.2005 | P0-1 AdEx model | `src/bnsyn/neuron/adex.py`, `src/bnsyn/sim/network.py` | `tests/test_adex_smoke.py`, `tests/test_network_smoke.py` |
| CLM-0003 | Tier-A | true | PROVEN | jahr1990voltage | 10.1523/JNEUROSCI.10-09-03178.1990 | P0-2 NMDA block | `src/bnsyn/synapse/conductance.py` | `tests/test_synapse_smoke.py` |
| CLM-0004 | Tier-A | true | PROVEN | fremaux2016neuromodulated | 10.3389/fncir.2015.00085 | P0-3 Three-factor learning | `src/bnsyn/plasticity/three_factor.py` | `tests/test_plasticity_smoke.py` |
| CLM-0005 | Tier-A | true | PROVEN | izhikevich2007solving | 10.1093/cercor/bhl152 | P0-3 Neuromodulated STDP | `src/bnsyn/plasticity/three_factor.py` | `tests/test_plasticity_smoke.py` |
| CLM-0006 | Tier-A | true | PROVEN | beggs2003neuronal | 10.1523/JNEUROSCI.23-35-11167.2003 | P0-4 Avalanche exponents | `src/bnsyn/criticality/branching.py` | `tests/test_criticality_smoke.py` |
| CLM-0007 | Tier-A | true | PROVEN | beggs2003neuronal | 10.1523/JNEUROSCI.23-35-11167.2003 | P0-4 Branching parameter σ | `src/bnsyn/criticality/branching.py` | `tests/test_criticality_smoke.py` |
| CLM-0008 | Tier-A | true | PROVEN | wilting2018inferring | 10.1038/s41467-018-04725-4 | P0-4 MR estimator | `src/bnsyn/criticality/analysis.py` | `tests/validation/test_criticality_validation.py` |
| CLM-0009 | Tier-A | true | PROVEN | clauset2009power | 10.1137/070710111 | P0-4 Power-law fitting | `src/bnsyn/criticality/analysis.py` | `tests/validation/test_criticality_validation.py` |
| CLM-0010 | Tier-A | true | PROVEN | frey1997synaptic | 10.1038/385533a0 | P1-6 Synaptic tagging | `src/bnsyn/consolidation/dual_weight.py` | `tests/test_consolidation_smoke.py` |
| CLM-0019 | Tier-A | true | PROVEN | kirkpatrick1983annealing | 10.1126/science.220.4598.671 | P1-5 Temperature schedule | `src/bnsyn/temperature/schedule.py` | `tests/test_temperature_smoke.py` |
| CLM-0020 | Tier-A | true | PROVEN | benna2016synaptic | 10.1038/nn.4401 | P1-6 Dual-weight consolidation | `src/bnsyn/consolidation/dual_weight.py` | `tests/test_consolidation_smoke.py`, `tests/validation/test_consolidation_validation.py` |
| CLM-0021 | Tier-A | true | PROVEN | hopfield1982neural | 10.1073/pnas.79.8.2554 | P1-7 Energy regularization | `src/bnsyn/energy/regularization.py` | `tests/test_energy_smoke.py`, `tests/validation/test_energy_validation.py` |
| CLM-0022 | Tier-A | true | PROVEN | hairer1993solving | 10.1007/978-3-540-78862-1 | P2-8 Numerical methods | `src/bnsyn/numerics/integrators.py` | `tests/test_dt_invariance.py`, `tests/validation/test_numerics_validation.py` |
| CLM-0023 | Tier-A | true | PROVEN | matsumoto1998mersenne | 10.1145/272991.272995 | P2-9 Determinism protocol | `src/bnsyn/rng.py`, `src/bnsyn/sim/network.py` | `tests/test_determinism.py`, `tests/validation/test_determinism_validation.py` |
| CLM-0024 | Tier-A | true | PROVEN | bjorck1996least | 10.1137/1.9781611971484 | P2-10 Calibration utilities | `src/bnsyn/calibration/fit.py` | `tests/test_calibration_smoke.py`, `tests/validation/test_calibration_validation.py` |
| CLM-0025 | Tier-A | true | PROVEN | izhikevich2003simple | 10.1109/TNN.2003.820440 | P2-11 Reference network simulator | `src/bnsyn/sim/network.py` | `tests/test_network_smoke.py`, `tests/validation/test_network_validation.py` |
| CLM-0026 | Tier-S | false | PROVEN | cliguidelines2024 | https://clig.dev/ | P2-12 Bench harness contract | `src/bnsyn/cli.py` | `tests/test_cli_smoke.py`, `tests/validation/test_cli_validation.py` |
| CLM-0011 | Tier-A | true | PROVEN | wilkinson2016fair | 10.1038/sdata.2016.18 | P2-8..12 FAIR principles | `scripts/validate_bibliography.py`, `scripts/validate_claims.py`, `scripts/scan_normative_tags.py` | `scripts/validate_bibliography.py`, `scripts/validate_claims.py`, `scripts/scan_normative_tags.py` |
| CLM-0012 | Tier-S | false | PROVEN | neurips2026checklist | https://neurips.cc/public/guides/PaperChecklist | P2-8..12 Reproducibility checklist | `scripts/validate_claims.py` | `scripts/validate_claims.py` |
| CLM-0013 | Tier-S | false | PROVEN | acm2020badges | https://www.acm.org/publications/policies/artifact-review-and-badging-current | P2-8..12 Artifact badges | `scripts/validate_claims.py` | `scripts/validate_claims.py` |
| CLM-0014 | Tier-S | false | PROVEN | pytorch2026randomness | https://pytorch.org/docs/stable/notes/randomness.html | P2-8..12 Determinism docs | `scripts/validate_claims.py` | `scripts/validate_claims.py` |
| CLM-0015 | Tier-A | true | PROVEN | trivers1971reciprocal | 10.1086/406755 | GOV-1 Result-based reciprocity (foundation) | `src/bnsyn/vcg.py` | `tests/test_vcg_smoke.py` |
| CLM-0016 | Tier-A | true | PROVEN | axelrod1981cooperation | 10.1126/science.7466396 | GOV-1 Symmetric reciprocity (tit-for-tat) | `src/bnsyn/vcg.py` | `tests/test_vcg_smoke.py` |
| CLM-0017 | Tier-A | true | PROVEN | nowak1998imagescoring | 10.1038/31225 | GOV-1 Reputation / indirect reciprocity | `src/bnsyn/vcg.py` | `tests/test_vcg_smoke.py` |
| CLM-0018 | Tier-A | true | PROVEN | fehr2002punishment | 10.1038/415137a | GOV-1 Costly sanctioning / defector suppression | `src/bnsyn/vcg.py` | `tests/test_vcg_smoke.py` |
