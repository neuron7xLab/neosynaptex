# Reviewer Guide — NeoSynaptex γ-Criticality Claim

> **Audience:** reviewers, replication-focused researchers, anyone
> asking *"where exactly does this claim come from and how do I verify
> it?"*
>
> This document is a flat, file:line map from every headline claim to
> the code, data, and ledger entries that produce it. It assumes you
> have cloned the repo and can run `pytest tests/ -q`.

---

## Quick start (10 minutes, no data download)

```bash
git clone https://github.com/neuron7xLab/neosynaptex.git
cd neosynaptex
pip install -e ".[dev]"

# 1. Reproduce the γ table for all substrates
python reproduce.py

# 2. Run the full non-slow test suite (431 tests, ~4 min)
pytest tests/ -q -m "not slow" --timeout=300

# 3. Run CI canonical gates and manuscript-claim verification
python scripts/ci_canonical_gate.py
python scripts/verify_manuscript_claims.py
```

All three must exit with status 0 on a clean checkout of `main`.

Alternatively, one-command Docker reproduction:

```bash
docker build -f Dockerfile.reproduce -t neosynaptex-repro .
docker run --rm neosynaptex-repro
```

---

## The headline claim

> **γ ≈ 1 across 10 independent substrates, 4 of which are wild
> empirical witnesses. One substrate (cfp_diy) reports γ ≈ 1.83,
> which is recorded as an out-of-regime falsifying control rather
> than hidden.**

The full tier-by-tier count is in
[`evidence/gamma_provenance.md`](../evidence/gamma_provenance.md).

---

## Claim ↔ code/data map

### Per-substrate γ values

Every value in the ledger is backed by an adapter under `substrates/`
and a test under `tests/`. The table below is the minimal map.

| Substrate | γ | 95 % CI | Adapter | Tests | Ledger key |
|-----------|---|---------|---------|-------|------------|
| eeg_physionet (T1) | 1.068 | [0.877, 1.246] | [`substrates/eeg_physionet/adapter.py`](../substrates/eeg_physionet/adapter.py) | [`tests/test_integrity_v2.py::TestEEG`](../tests/test_integrity_v2.py) | `eeg_physionet` |
| eeg_resting (T1) | 1.255 | [1.032, 1.452] | [`substrates/eeg_resting/adapter.py`](../substrates/eeg_resting/adapter.py) | [`tests/test_eeg_resting_substrate.py`](../tests/test_eeg_resting_substrate.py) | `eeg_resting` |
| hrv_physionet (T1) | 0.885 | [0.834, 1.080] | [`substrates/hrv_physionet/adapter.py`](../substrates/hrv_physionet/adapter.py) | [`tests/test_integrity_v2.py::TestHRV`](../tests/test_integrity_v2.py) | `hrv_physionet` |
| hrv_fantasia (T1) | 1.003 | [0.935, 1.059] | [`substrates/hrv_fantasia/adapter.py`](../substrates/hrv_fantasia/adapter.py) | [`tests/test_hrv_fantasia_substrate.py`](../tests/test_hrv_fantasia_substrate.py) | `hrv_fantasia` |
| zebrafish_wt (T2) | 1.055 | [0.890, 1.210] | [`substrates/zebrafish/adapter.py`](../substrates/zebrafish/adapter.py) | [`tests/test_zebrafish_real.py`](../tests/test_zebrafish_real.py) | `zebrafish_wt` |
| gray_scott (T3) | 0.979 | [0.880, 1.010] | [`substrates/gray_scott/adapter.py`](../substrates/gray_scott/adapter.py) | [`tests/test_gray_scott_real.py`](../tests/test_gray_scott_real.py) | `gray_scott` |
| kuramoto_market (T3) | 0.963 | [0.930, 1.000] | [`substrates/kuramoto/adapter.py`](../substrates/kuramoto/adapter.py) | [`tests/test_kuramoto_real.py`](../tests/test_kuramoto_real.py) | `kuramoto` |
| bn_syn (T3) | 0.946 | [0.810, 1.080] | [`substrates/bn_syn/adapter.py`](../substrates/bn_syn/adapter.py) | [`tests/test_bnsyn_real.py`](../tests/test_bnsyn_real.py) | `bnsyn` |
| serotonergic_kuramoto (T5) | 1.068 | [0.145, 1.506] | [`substrates/serotonergic_kuramoto/adapter.py`](../substrates/serotonergic_kuramoto/adapter.py) | [`tests/test_serotonergic_kuramoto.py`](../tests/test_serotonergic_kuramoto.py), [`tests/test_calibration_robustness.py`](../tests/test_calibration_robustness.py) | `serotonergic_kuramoto` |
| cfp_diy (T3†, out-of-regime) | 1.832 | [1.638, 1.978] | [`substrates/cfp_diy/adapter.py`](../substrates/cfp_diy/adapter.py) | [`tests/test_cfp_diy.py`](../tests/test_cfp_diy.py) | `cfp_diy` |

The authoritative γ numbers live in
[`evidence/gamma_ledger.json`](../evidence/gamma_ledger.json). Every
entry carries `adapter_code_hash` (SHA-256 of the adapter file at
measurement time) and, where available, a `bootstrap_metadata` block
with full CI + permutation p-value + R².

### γ core computation

All γ values flow through a single function:

- [`core/gamma.py::compute_gamma`](../core/gamma.py) — Theil-Sen
  log-log regression, bootstrap CI (n=500), verdict classifier.
- [`core/bootstrap.py::bootstrap_summary`](../core/bootstrap.py) —
  per-unit γ population summary with permutation p-value.
- [`core/bootstrap.py::permutation_p_value`](../core/bootstrap.py) —
  paired (topo, cost) permutation test for log-log fits.

### Axiom and invariants

- [`core/axioms.py`](../core/axioms.py) — AXIOM_0 statement,
  `SUBSTRATE_GAMMA` registry pulled from the ledger (no hard-coded γ).
- [`core/gamma_registry.py`](../core/gamma_registry.py) — single
  source of truth for ledger access; enforces invariant
  *γ DERIVED ONLY — never assigned, never input parameter*.

### Ledger provenance
- [`evidence/gamma_ledger.json`](../evidence/gamma_ledger.json)
- [`evidence/gamma_provenance.md`](../evidence/gamma_provenance.md) —
  T1…T5 tier classification with falsification conditions per
  substrate.
- [`evidence/data_hashes.json`](../evidence/data_hashes.json) —
  SHA-256 hashes of every external data file used by T1 substrates.
- [`evidence/PREREG.md`](../evidence/PREREG.md) — pre-registration
  commit hashes proving that each substrate’s code (and hence its
  expected γ) was committed before the measurement was written into
  the ledger.

### CI gates

Every claim in the repo is enforced by at least one of:

- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) — NFI CI
  (lint, mypy, tests, canonical gate, invariant tests, license
  boundaries, coverage).
- [`.github/workflows/docker-reproduce.yml`](../.github/workflows/docker-reproduce.yml)
  — builds `Dockerfile.reproduce` on every relevant push and runs a
  smoke test of the entrypoint.
- [`scripts/ci_canonical_gate.py`](../scripts/ci_canonical_gate.py)
  — 6 gates: gamma_provenance, evidence_hash, split_brain,
  math_core_tested, invariant_gamma, testpath_hermetic.
- [`scripts/verify_manuscript_claims.py`](../scripts/verify_manuscript_claims.py)
  — 20 manuscript claims cross-checked against the ledger.
- [`scripts/check_license_boundaries.py`](../scripts/check_license_boundaries.py)
  — AGPL zone enforcement.
- [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) — local
  mirror of the CI lint/format/test gates so that broken commits are
  blocked before they leave the laptop.

### Falsification and negative controls

All negative controls live in one file for easy review:
[`tests/test_falsification_negative.py`](../tests/test_falsification_negative.py).

Eight tests prove that γ *breaks* when it should:

1. `test_gamma_breaks_under_shuffled_topo` — clean signal, shuffle the
   topo array → γ leaves [0.7, 1.3] or verdict becomes LOW_R2.
2. `test_gamma_breaks_under_random_cost` — uniform-log cost noise.
3. `test_brownian_1_over_f_squared_reports_gamma_near_2` — Brownian
   PSD returns γ ≈ 2.3 (observed), not 1.
4. `test_permutation_rejects_pure_noise` — p > 0.05 on pure noise.
5-7. Per-substrate shuffles (`slow`): serotonergic, gray_scott,
   kuramoto. All three see their γ collapse when the topo array is
   shuffled.
8. `test_exponential_decay_not_metastable` — exponential decay → γ
   outside window.

### Reproducibility guarantees

- **Bit-exact:** every γ value is reproducible from seed=42 on the
  same code. Tests for this:
  - `tests/test_calibration_robustness.py` — serotonergic_kuramoto
  - `tests/test_eeg_resting_substrate.py::test_reproducibility_bitexact`
  - `tests/test_hrv_fantasia_substrate.py::test_reproducibility_bitexact`
  - `tests/test_bootstrap_helpers.py::test_bootstrap_summary_is_deterministic_under_seed`
- **Data integrity:** SHA-256 hashes of every T1 data file are
  verified on every full-test run (`tests/test_eeg_resting_substrate.py`,
  `tests/test_hrv_fantasia_substrate.py`).
- **Environment:** `Dockerfile.reproduce` pins Python 3.12 and
  installs `-e ".[dev]"` plus optional mne/specparam/wfdb for the
  empirical substrates. CI validates the image on every relevant push.

---

## How to verify each claim independently

| You want to verify… | Run |
|---|---|
| γ ≈ 1 across all substrates | `python reproduce.py` |
| γ is bit-exact reproducible | `pytest tests/test_bootstrap_helpers.py tests/test_calibration_robustness.py tests/test_eeg_resting_substrate.py tests/test_hrv_fantasia_substrate.py` |
| Falsification controls work | `pytest tests/test_falsification_negative.py` |
| T1 EEG Welch γ = 1.26 on real PhysioNet data | `python -c "from substrates.eeg_resting.adapter import run_gamma_analysis; run_gamma_analysis()"` |
| T1 HRV DFA γ = 1.00 on real Fantasia data | `python -c "from substrates.hrv_fantasia.adapter import run_gamma_analysis; run_gamma_analysis()"` |
| Serotonergic basin width 0.010 Hz | `pytest tests/test_calibration_robustness.py -v -s` |
| Manuscript claims match ledger | `python scripts/verify_manuscript_claims.py` |
| Canonical gates pass | `python scripts/ci_canonical_gate.py` |
| Image builds and reproduces | `docker build -f Dockerfile.reproduce -t t .; docker run --rm t` |

---

## What is intentionally NOT in scope

- Any claim about psychedelic pharmacology beyond what the
  serotonergic_kuramoto substrate literally tests. The Kuramoto
  mapping is **a calibrated model**, not a prediction about humans.
- Any clinical application of the cardiac or EEG substrates. They are
  1/f spectral-slope replications on public data, nothing more.
- cns_ai_loop and nfi_unified (T4) are excluded from the headline
  count. See `evidence/gamma_provenance.md` for why.

Where a limitation is known to us, it is listed in
[`docs/KNOWN_LIMITATIONS.md`](./KNOWN_LIMITATIONS.md) with the
severity classification and the next-step mitigation.

---

**Last audit:** 2026-04-05. Provenance frozen against commit
`git rev-parse HEAD`.
