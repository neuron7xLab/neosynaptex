# Traceability Matrix

> **Purpose:** Maps each scientific invariant to the test that verifies it,
> the code that implements it, and the proof/evidence that establishes it.
>
> This matrix is the audit trail for the claim that every headline result
> is mechanically verifiable from the repository.

---

## Format

Each row has:
- **Invariant** — the claim being traced
- **Test** — the pytest test(s) that verify the invariant
- **Code** — the implementation file(s)
- **Proof / Evidence** — the ledger entry, data file, or formal proof

---

## Core Gamma Invariants

| Invariant | Test | Code | Proof |
|-----------|------|------|-------|
| gamma derived only, never assigned | `tests/test_gamma_registry.py` | `core/gamma_registry.py` | `evidence/gamma_ledger.json` (invariant field) |
| gamma CI requires bootstrap n >= 500 | `tests/test_bootstrap_helpers.py::test_bootstrap_n` | `neosynaptex.py::_BOOTSTRAP_N`, `core/gamma.py` | `evidence/gamma_ledger.json` (bootstrap_metadata) |
| gamma estimator is Theil-Sen (not OLS) | `tests/test_integrity_v2.py::test_theil_sen_used` | `core/gamma.py::compute_gamma` | [ADR-003](../adr/ADR-003-theil-sen-estimator.md) |
| log-range gate >= 0.5 required | `tests/test_integrity_v2.py::test_log_range_gate` | `neosynaptex.py::_LOG_RANGE_GATE` | `PROTOCOL.md` |
| R2 gate >= 0.3 required for METASTABLE | `tests/test_integrity_v2.py::test_r2_gate` | `neosynaptex.py::_R2_GATE` | `PROTOCOL.md` |

---

## Per-Substrate Gamma Claims

| Invariant | Test | Code | Proof |
|-----------|------|------|-------|
| zebrafish gamma in [0.85, 1.15] | `tests/test_integrity_v2.py::TestZebrafish` | `substrates/zebrafish/adapter.py` | `evidence/gamma_ledger.json::zebrafish_wt` |
| eeg_physionet gamma in [0.85, 1.15] | `tests/test_integrity_v2.py::TestEEG` | `substrates/eeg_physionet/adapter.py` | `evidence/gamma_ledger.json::eeg_physionet` |
| eeg_resting gamma CI contains 1.0 | `tests/test_eeg_resting_substrate.py` | `substrates/eeg_resting/adapter.py` | `evidence/gamma_ledger.json::eeg_resting` |
| hrv_physionet gamma in [0.75, 1.15] | `tests/test_integrity_v2.py::TestHRV` | `substrates/hrv_physionet/adapter.py` | `evidence/gamma_ledger.json::hrv_physionet` |
| hrv_fantasia gamma CI contains 1.0 | `tests/test_hrv_fantasia_substrate.py` | `substrates/hrv_fantasia/adapter.py` | `evidence/gamma_ledger.json::hrv_fantasia` |
| gray_scott gamma in [0.85, 1.15] | `tests/test_gray_scott_real.py` | `substrates/gray_scott/adapter.py` | `evidence/gamma_ledger.json::gray_scott` |
| kuramoto gamma in [0.85, 1.15] | `tests/test_kuramoto_real.py` | `substrates/kuramoto/adapter.py` | `evidence/gamma_ledger.json::kuramoto` |
| bn_syn gamma in [0.85, 1.15] | `tests/test_bnsyn_real.py` | `substrates/bn_syn/adapter.py` | `evidence/gamma_ledger.json::bnsyn` |
| serotonergic_kuramoto gamma CI contains 1.0 | `tests/test_serotonergic_kuramoto.py` | `substrates/serotonergic_kuramoto/adapter.py` | `evidence/gamma_ledger.json::serotonergic_kuramoto` |
| cfp_diy documented as out-of-regime | `tests/test_cfp_diy.py::test_out_of_regime_documented` | `substrates/cfp_diy/adapter.py` | `evidence/gamma_ledger.json::cfp_diy` |

---

## Falsification / Negative Controls

| Invariant | Test | Code | Proof |
|-----------|------|------|-------|
| Shuffled topo breaks gamma | `tests/test_falsification_negative.py::test_gamma_breaks_under_shuffled_topo` | `core/gamma.py` | `tests/test_falsification_negative.py` |
| Random cost breaks gamma | `tests/test_falsification_negative.py::test_gamma_breaks_under_random_cost` | `core/gamma.py` | `tests/test_falsification_negative.py` |
| Brownian 1/f^2 returns gamma near 2 | `tests/test_falsification_negative.py::test_brownian_1_over_f_squared` | `core/gamma.py` | `tests/test_falsification_negative.py` |
| Permutation rejects pure noise | `tests/test_falsification_negative.py::test_permutation_rejects_pure_noise` | `core/bootstrap.py::permutation_p_value` | `tests/test_falsification_negative.py` |
| Exponential decay not METASTABLE | `tests/test_falsification_negative.py::test_exponential_decay_not_metastable` | `neosynaptex.py` | `tests/test_falsification_negative.py` |

---

## Reproducibility Invariants

| Invariant | Test | Code | Proof |
|-----------|------|------|-------|
| gamma is bit-exact reproducible (seed=42) | `tests/test_calibration_robustness.py` | `neosynaptex.py`, `core/gamma.py` | `reproduce.py` |
| eeg_resting bit-exact reproducibility | `tests/test_eeg_resting_substrate.py::test_reproducibility_bitexact` | `substrates/eeg_resting/adapter.py` | `evidence/data_hashes.json` |
| hrv_fantasia bit-exact reproducibility | `tests/test_hrv_fantasia_substrate.py::test_reproducibility_bitexact` | `substrates/hrv_fantasia/adapter.py` | `evidence/data_hashes.json` |
| bootstrap is deterministic under seed | `tests/test_bootstrap_helpers.py::test_bootstrap_summary_is_deterministic_under_seed` | `core/bootstrap.py` | `tests/test_bootstrap_helpers.py` |
| T1 data SHA-256 hashes match | `tests/test_eeg_resting_substrate.py::test_data_hash`, `tests/test_hrv_fantasia_substrate.py::test_data_hash` | `evidence/data_hashes.json` | `evidence/data_hashes.json` |

---

## Axiom and Invariant Verification

| Invariant | Test | Code | Proof |
|-----------|------|------|-------|
| AXIOM_0: mean gamma across substrates | `tests/test_axioms.py` | `core/axioms.py::verify_axiom_consistency` | `evidence/gamma_ledger.json` |
| Invariant VI: ASCII-only identifiers | `make lint` (`ruff`) | all source files | `PROTOCOL.md::Invariant VI` |
| MAX_DOMAINS = 4 | `tests/test_integrity_v2.py::test_max_domains` | `neosynaptex.py::_MAX_STATE_KEYS` | `PROTOCOL.md` |
| License boundaries enforced | `tests/test_license_boundaries.py` | `scripts/check_license_boundaries.py` | `LICENSE_BOUNDARIES.md` |

---

## CI Gates

| Gate | CI check | Code | Evidence |
|------|----------|------|---------|
| gamma_provenance | `scripts/ci_canonical_gate.py::gate_gamma_provenance` | `evidence/gamma_provenance.md` | CI log |
| evidence_hash | `scripts/ci_canonical_gate.py::gate_evidence_hash` | `evidence/data_hashes.json` | CI log |
| split_brain | `scripts/ci_canonical_gate.py::gate_split_brain` | `core/gamma_registry.py` | CI log |
| math_core_tested | `scripts/ci_canonical_gate.py::gate_math_core_tested` | `core/*.py` | CI log |
| invariant_gamma | `scripts/ci_canonical_gate.py::gate_invariant_gamma` | `evidence/gamma_ledger.json` | CI log |
| testpath_hermetic | `scripts/ci_canonical_gate.py::gate_testpath_hermetic` | `tests/` | CI log |

---

## Kuramoto-specific Traceability

For the Kuramoto substrate, a more detailed traceability matrix is available
at [`docs/traceability/kuramoto_traceability_matrix.md`](kuramoto_traceability_matrix.md).
