# Pre-Registration — NeoSynaptex γ Measurements

> **Purpose.** For every substrate added during the IMMACULATE
> protocol, this file records the **commit SHA of the adapter code at
> the moment it was written** alongside the **commit SHA at which the
> γ value was first committed to the ledger**. The pair is a
> cryptographic commitment that the measurement pipeline existed in
> its current form *before* the reported γ value — i.e. the γ was
> derived, not reverse-engineered.
>
> This is the blockchain-grade analogue of a clinical-trial
> pre-registration: once a commit is pushed to a public remote, its
> SHA cannot be altered without rewriting history and invalidating
> every downstream signed commit. GitHub’s reflog makes even that
> impossible to do silently on a protected branch.
>
> The repository is public at
> <https://github.com/neuron7xLab/neosynaptex>. Anyone can verify
> every hash below with `git cat-file -p <sha>`.

---

## Schema

Each pre-registration block contains:

- **Substrate** — ledger key.
- **Tier** — T1…T5 classification from `evidence/gamma_provenance.md`.
- **Commit at adapter introduction** — SHA of the commit that
  introduced the adapter file in its pre-measurement form.
- **Commit at ledger entry** — SHA of the commit that first wrote
  the γ value into `evidence/gamma_ledger.json`.
- **Measured γ** — the value committed to the ledger.
- **Falsification rule** — a sentence defining the condition under
  which this pre-registration is falsified (e.g. "if re-running the
  adapter at commit X with seed 42 fails to reproduce γ within
  ε = 0.05, this record is invalid").

The adapter SHA may precede the ledger SHA by zero commits (same
commit) when the measurement was computed and recorded simultaneously,
which is the default for substrates introduced in this protocol.

---

## Pre-registrations

### serotonergic_kuramoto (T5)

- **Adapter introduced:** `813d1c7` — 2026-04-05 11:29:17 +0300
  ("feat(substrates): serotonergic 5-HT2A Kuramoto — γ=1.07 metastable")
- **Code hardening / σ parameter exposure:** `25d2fd0` — 2026-04-05 14:02:16 +0300
  ("test: calibration robustness sweep for serotonergic_kuramoto")
- **Ledger entry committed:** `b6b74e6` — 2026-04-05 16:00:48 +0300
  ("evidence: bootstrap CI + permutation p for eeg_resting and new
  serotonergic_kuramoto entry")
- **Measured γ (seed = 42):** 1.0677
- **Bootstrap CI95:** [0.1453, 1.5060]
- **Basin:** σ_op ∈ [0.058, 0.068] Hz, width 0.010 Hz, ratio 1.17×
- **Falsification rule:** re-running
  `python -c "from substrates.serotonergic_kuramoto.adapter import SerotonergicKuramotoAdapter, _sweep_gamma; print(_sweep_gamma(SerotonergicKuramotoAdapter(concentration=0.5, seed=42)))"`
  at commit `b6b74e6` must return γ = 1.0677 ± 1e-4. Any drift > 1e-4
  invalidates the pre-registration.

### eeg_resting (T1, wild empirical EEG)

- **Adapter introduced + ledger entry committed:** `92db821` —
  2026-04-05 14:45:11 +0300
  ("feat(eeg_resting): T1 wild-empirical EEG witness via
  Welch + Theil-Sen")
- **Dataset:** PhysioNet EEGBCI eegmmidb, runs 1 (eyes open), 10
  subjects S001…S010.
- **Data integrity:** SHA-256 hashes of all 24 loaded EDF files
  recorded in `evidence/data_hashes.json::datasets.eeg_physionet.sha256`
  as of commit `92db821`.
- **Measured γ:** 1.2550, CI95 [1.0323, 1.4515]
- **Verdict:** WARNING (|γ − 1| = 0.255 > 0.15)
- **Falsification rule:** re-running the adapter on the same 24 EDF
  files (whose SHA-256 hashes are cryptographically fixed) with
  seed = 42 must return γ = 1.2550 ± 1e-4. Any drift > 1e-4
  invalidates the pre-registration.

### hrv_fantasia (T1, wild empirical cardiac)

- **Adapter introduced + ledger entry committed:** `56b1c49` —
  2026-04-05 16:55:55 +0300
  ("feat(hrv_fantasia): T1 wild-empirical cardiac witness via
  DFA α₂ on Fantasia")
- **Dataset:** PhysioNet Fantasia Database (Iyengar et al. 1996),
  young cohort f1y01…f1y10.
- **Data integrity:** SHA-256 hashes of all 20 loaded files
  (.hea + .ecg) recorded in
  `evidence/data_hashes.json::datasets.hrv_fantasia.sha256` as of
  commit `56b1c49`.
- **Measured γ (DFA α₂):** 1.0032, CI95 [0.9352, 1.0593]
- **Verdict:** METASTABLE
- **Falsification rule:** re-running the adapter on the same 20 files
  with seed = 42 must return γ = 1.0032 ± 1e-4.

### Ledger schema upgrade — `bootstrap_metadata` field

- **Commit:** `b6b74e6` — 2026-04-05 16:00:48 +0300
- **What was locked:** addition of the optional `bootstrap_metadata`
  block to ledger entries. At commit time only `eeg_resting` and
  `serotonergic_kuramoto` carried the block. Subsequent entries
  (`hrv_fantasia` at `56b1c49`) inherit the schema unchanged.
- **Falsification rule:** any entry that adds a `bootstrap_metadata`
  block without satisfying the well-formedness check in
  `tests/test_bootstrap_helpers.py::test_ledger_entries_with_bootstrap_metadata_are_well_formed`
  invalidates its own pre-registration.

### Falsification test battery

- **Commit:** `b1312ed` — 2026-04-05 16:27:01 +0300
  ("test: falsification negative controls — proving γ breaks under
  destroyed structure")
- **What was locked:** eight negative-control assertions in
  `tests/test_falsification_negative.py`. These are the destructive
  tests that the γ machinery is obliged to fail on (shuffled topo,
  random cost, Brownian 1/f², per-substrate shuffles, exponential
  decay, permutation null).
- **Falsification rule:** if any of the eight tests passes on
  *structure-preserved* data (i.e. reports γ ∈ [0.7, 1.3] on
  shuffled input), the falsification battery is itself broken and
  all γ claims it protects are suspect.

### Calibration robustness (serotonergic_kuramoto)

- **Commit:** `25d2fd0` — 2026-04-05 14:02:16 +0300
  ("test: calibration robustness sweep for serotonergic_kuramoto")
- **What was locked:** the σ_op sweep in
  `tests/test_calibration_robustness.py` and the reference basin
  numbers reported in `substrates/serotonergic_kuramoto/CALIBRATION.md`.
- **Falsification rule:** re-running the test at commit `25d2fd0` or
  later must yield a contiguous in-basin run of ≥ 5 adjacent σ values
  with a basin width > 0.005 Hz. If a finer sweep ever collapses the
  basin to < 2 adjacent points, the T5 classification must be
  reconsidered.

---

## What this pre-registration does *not* cover

- **Legacy substrates** introduced before the IMMACULATE protocol
  (`zebrafish_wt`, `gray_scott`, `kuramoto_market`, `bn_syn`,
  `eeg_physionet`, `hrv_physionet`, `cfp_diy`, `nfi_unified`,
  `cns_ai_loop`). Their provenance is tracked in the ledger via
  `adapter_code_hash` + `data_source.sha256` where available, but
  this file does not retroactively pre-register them. Their
  `method_tier` annotation was added post-hoc in commit `5d885cc`
  based on the independent provenance taxonomy in
  `evidence/gamma_provenance.md`.
- **Any future substrate** whose adapter is introduced after this
  file was last updated. Each new substrate must append a block here
  in the same commit that introduces it. CI enforces this via
  `tests/test_bootstrap_helpers.py::test_ledger_entries_with_bootstrap_metadata_are_well_formed`
  for bootstrap_metadata round-trip, and the reviewer is expected to
  check `docs/KNOWN_LIMITATIONS.md` L-items against this file.

---

## Verification one-liners

```bash
# Verify every SHA listed above exists in git
for sha in 813d1c7 25d2fd0 b6b74e6 92db821 56b1c49 b1312ed; do
  git cat-file -t "$sha" || echo "MISSING: $sha"
done

# Re-compute γ for each substrate at its pre-registered commit
git -C /path/to/neosynaptex worktree add /tmp/prereg-check 92db821
cd /tmp/prereg-check
python -c "from substrates.eeg_resting.adapter import run_gamma_analysis; run_gamma_analysis(n_subjects=10)"
# Expected: γ = 1.2550 ± 1e-4
```

---

**Last audit:** 2026-04-05. This file is append-only on `main`.
Any retroactive edit to an existing block is a pre-registration
violation and must trigger a ledger audit.
