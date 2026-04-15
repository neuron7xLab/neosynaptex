# External Replication Invitation — PhysioNet Cardiac HRV γ Pilot

> **Status.** Open invitation. Version 1, filed 2026-04-14.
> **Scope.** Two substrates from the 2026-04-14 PhysioNet cardiac
> HRV pilot: NSR2DB multifractal (n=5, healthy) and CHF2DB pathology
> contrast (n=5 CHF vs n=5 NSR). Both currently carry
> `claim_status: measured_but_bounded`. Per
> `docs/CLAIM_BOUNDARY.md` §2 and `docs/REPLICATION_PROTOCOL.md` §3,
> neither substrate's claim promotes beyond `measured_but_bounded`
> until at least one independent laboratory reproduces the results
> from the locked manifest below.
> **Companion.** `docs/REPLICATION_PROTOCOL.md` is the parent
> protocol; this file is a practical entry point that locks every
> operational parameter an external lab needs.

## 1. What we ask

Run the frozen pipeline on the frozen data, cross-sign the outputs,
and file a report. We require:

- Data SHA match against the manifest in §4 (byte-identical RR
  series after the fixed preprocessing).
- γ, Δh, and h(q=2) per-subject within the tolerance window in §7.
- Beat-interval-null separation count matching ours (or a
  documented deviation).
- A signed `external_replication_result.json` filed at
  `evidence/replications/external/<lab_slug>_<YYYY-MM-DD>_<substrate>/`
  and a PR to the registry (`evidence/replications/registry.yaml`)
  adding an `external_replications` list to the corresponding entry.

We **do not** require the external lab to match our claim framing.
A replication that produces different γ or rejects the pattern is a
first-class result under `docs/REPLICATION_PROTOCOL.md` §3 and
enters the ledger with equal status to a confirming replication.

## 2. Why external replication gates the claim

The owner-recorded trajectory (2026-04-14, `SESSION_CLOSE_2026-04-14.md`):

- n=1 NSR2DB pilot → γ ≈ 1.0855, IAAFT not separable → revealed a
  linear-signature gap.
- n=5 NSR2DB multifractal pilot → γ mean **0.50 ± 0.44**, Δh = 0.19,
  beat-null separates on 4/5. Cross-subject γ **not** near 1.0;
  n=1 was an outlier.
- n=5 NSR vs n=5 CHF contrast → Cohen d = −2.56 on h(q=2), +1.85 on
  Δh. FIRST POSITIVE within-substrate finding.

All three results were produced by the same estimator implementer.
The replication protocol (Hengen & Shew 2025 precedent,
`docs/REPLICATION_PROTOCOL.md` §4) is explicit that same-group
replication is weaker than independent replication, and that no
cross-substrate or cross-population claim is licensed from a
single-lab pilot. This invitation asks an external lab to collapse
that uncertainty.

## 3. Environment lock

The originating run used:

```
python    3.12.3
wfdb      4.3.1
scipy     1.17.1
numpy     2.4.3
seed      42
os        linux (kernel-agnostic; no OS-specific code paths)
```

You may use a different environment **provided** the RR-series
SHA-256 values in §4 still match after your preprocessing. If the
SHAs mismatch, stop and file a mismatch report — something has
drifted (wfdb API change, PhysioNet republication, or an
interpretation difference on the annotation filter).

## 4. Data manifest (SHA-locked)

All records fetched via `wfdb.rdann(record, "ecg", pn_dir=<db>)`
then filtered to symbol == `"N"` and truncated to the first
**20,000** RR intervals. The SHA-256 is over the `float64` numpy
array of RR-interval seconds serialised in C order (same ordering
produced by `rr_to_uniform_4hz`'s input path; see
`substrates/physionet_hrv/nsr2db_client.py`).

### NSR2DB (`pn_dir="nsr2db"`)

| record  | n_normal_beats | fs_hz | rr_truncated_to | rr_sha256 |
|---------|---------------:|------:|----------------:|-----------|
| nsr001  | 106379 | 128.0 | 20000 | `461bdc30e26a8a7dc8ad1e848acf6e751cb09630d2152840c6bdb9c2a843ea99` |
| nsr002  | 111100 | 128.0 | 20000 | `f61dc40ebf5c33e02cc1622ffebdd39375ce95eca0e0a34f95de8f1529df52d7` |
| nsr003  |  97274 | 128.0 | 20000 | `da0e3bd3b4b41e20547a82a4ed49dfe9a0640d9e753f14c15012e69af331632d` |
| nsr004  |  97779 | 128.0 | 20000 | `ffdecb35ff9a2d655208353bb81217a987a476603899a477b10278cfe70c099f` |
| nsr005  | 116261 | 128.0 | 20000 | `1adb63b67e7ff6ca431576e2a7aca834344150d293b11e75a3548ab121693c93` |

### CHF2DB (`pn_dir="chf2db"`)

| record  | n_normal_beats | fs_hz | rr_truncated_to | rr_sha256 |
|---------|---------------:|------:|----------------:|-----------|
| chf201  | 112123 | 128.0 | 20000 | `04cc92049d8aa1e89ac2b20a484e829d697cc514822a3ded7126815cd6de1b51` |
| chf202  | 109059 | 128.0 | 20000 | `9ed97812073907ed1cfaf8e6779f476e58c132f0b456263f0aa644383cf51cbe` |
| chf203  |  98884 | 128.0 | 20000 | `12557f3ba1f4e11ea2a49e697c6c34aedbb7208b44a1647ad78b1dabe6d90b1e` |
| chf204  |  96320 | 128.0 | 20000 | `8ee9967197aa16520c4051eac9c7a83bd079a7c67d5fa986deb639e34f9f93c5` |
| chf205  | 133482 | 128.0 | 20000 | `a28c172125cc04c150be06f0d06e1dec6410847e51fa71c63584346a66677bfe` |

## 5. Pipeline lock

Originating implementation lives in:

- `substrates/physionet_hrv/nsr2db_client.py` — fetch + RR extraction.
- `substrates/physionet_hrv/chf2db_client.py` — CHF2DB variant.
- `substrates/physionet_hrv/hrv_gamma_fit.py` — RR → uniform-4Hz,
  Welch PSD, Theil-Sen slope on the VLF band.
- `substrates/physionet_hrv/mfdfa.py` — Kantelhardt 2002 MFDFA,
  numpy-only.
- `run_nsr2db_hrv_multifractal.py` — NSR pilot orchestrator.
- `run_chf2db_hrv_contrast.py` — CHF contrast orchestrator.

Frozen parameters:

```
# γ-fit (Welch-PSD + Theil-Sen)
fs_uniform_hz = 4.0
vlf_band_hz   = (0.003, 0.04)
nperseg       = 1024
detrend       = "constant"

# MFDFA
q_range = (-3.0, 3.0)
q_step  = 0.5           # ⇒ q ∈ {-3.0, -2.5, …, +3.0}
s_min   = 16
s_max   = rr_truncated // 4     # = 5000
n_scales = 20
fit_order = 1           # linear detrending of each segment

# Beat-interval null
n_surrogates       = 30
surrogate_source   = RR-sequence permutation BEFORE uniform resample
z_score_cutoff     = 3.0
ci_level           = 0.95

# Seed
seed = 42
```

The beat-interval null is the primary null-model claim. Shuffled,
IAAFT, and AR(1) are documented in the n=1 pilot
(`evidence/replications/physionet_nsr2db/prereg.yaml`) and need not
be re-run for this invitation unless a lab wants to verify those
baselines independently.

## 6. Reproduction command

```bash
git clone https://github.com/neuron7xLab/neosynaptex.git
cd neosynaptex
pip install wfdb scipy numpy

# Branch A — healthy multifractal:
python run_nsr2db_hrv_multifractal.py
# Output: evidence/replications/physionet_nsr2db_multifractal/result.json

# Branch B — pathology contrast:
python run_chf2db_hrv_contrast.py
# Output: evidence/replications/physionet_chf2db_contrast/result.json
```

Total runtime: ~3 minutes for both substrates on a modern laptop.
No GPU. No network after the initial `wfdb` fetch.

## 7. Acceptance tolerances

For each subject the external pipeline must produce:

| metric     | tolerance                                    |
|------------|----------------------------------------------|
| `rr_sha256` | exact match (no tolerance)                   |
| γ (`value`) | ± 0.01 vs this repo's result.json             |
| γ CI        | ± 0.02 on both bounds                         |
| Δh         | ± 0.01                                        |
| h(q=2)     | ± 0.01                                        |
| beat-null separable count | exact per-subject match (z > 3)   |

For the CHF-vs-NSR contrast:

| metric                  | tolerance |
|-------------------------|-----------|
| Welch t on h(q=2)        | ± 0.1     |
| Cohen d on h(q=2)        | ± 0.1     |
| Welch t on Δh            | ± 0.1     |
| Cohen d on Δh            | ± 0.1     |

Any out-of-tolerance result with matching SHAs is a **theory-revising
counterexample**, not a failure of the invitation. File it the
same way; it enters the ledger under `docs/REPLICATION_PROTOCOL.md`
§3 ("counterexamples update the theory, not the footnotes").

## 8. Reporting format

File a PR adding a directory:

```
evidence/replications/external/<lab_slug>_<YYYY-MM-DD>_<substrate>/
  ├── external_replication_result.json
  ├── environment.txt            # pip freeze; OS; Python version
  └── NOTES.md                   # deviations, if any
```

And extend the matching registry entry in
`evidence/replications/registry.yaml` with an `external_replications`
field:

```yaml
  - id: physionet_nsr2db_n5_multifractal_2026_04_14
    ...
    external_replications:
      - lab: <institution or individual>
        date: <YYYY-MM-DD>
        result_path: evidence/replications/external/<lab_slug>_<date>_<substrate>/external_replication_result.json
        verdict: confirmed | counterexample | partial
        notes: <one-sentence summary>
```

A companion audit script for the registry schema is not required
for the first external replication (schema extension can land in
the same PR). If external replications accrue in volume, a gate
analogous to `tools/audit/replication_index_check.py` may be added.

## 9. Claim-status gate

The substrate's registry entry stays at its current verdict
(`physionet_nsr2db_n5_multifractal_2026_04_14` → `theory_revision`;
`physionet_chf2db_pathology_contrast_2026_04_14` → `support`) and
the **claim_status** remains `measured_but_bounded` until at least
one external lab files a confirming replication per §7.

Once a confirming external replication is filed and merged, the
claim_status may promote to `measured_external_1lab`. Promotion
beyond that (to `measured_cross_lab`) requires n ≥ 2 independent
external labs per `docs/REPLICATION_PROTOCOL.md` §4.1.

No promotion is automatic. Each promotion is a claim-level change
and lands in a focused PR that audit-reviews the external report
against the tolerances in §7.

## 10. What this invitation does NOT license

- Clinical or diagnostic claims about CHF discrimination. The n=5
  vs n=5 pilot is a marker-discovery pilot, not a diagnostic study.
- Cross-substrate universal-γ framing. Both HRV substrates contradict
  substrate-independence at the n=5 pilot level (γ mean 0.50 ± 0.44
  cross-subject); `docs/CLAIM_BOUNDARY.md` §2 remains binding.
- Generalisation to AF, MI, valvular, or other cardiac pathologies.
  The marker passes a pilot contrast against one pathology cohort.
- Promotion of claim_status without matching SHAs. If your data SHAs
  do not match §4, the replication is inadmissible under this
  protocol; file a drift report separately.

## 11. Contact and licensing

Repository: https://github.com/neuron7xLab/neosynaptex
Licence: see `LICENSE` at repo root.
Corresponding maintainer: see `CODEOWNERS` (if present) or the
author field of `CITATION.cff`.

External labs or independent researchers may open a PR directly.
If a private pre-report review is needed before filing, open a
draft PR and tag the maintainer.

## 12. Changelog

| Version | Date       | Change |
|---------|------------|--------|
| 1.0     | 2026-04-14 | Initial open invitation covering NSR2DB n=5 multifractal and CHF2DB n=5 vs NSR n=5 contrast substrates. |
