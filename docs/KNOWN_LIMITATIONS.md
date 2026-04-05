# Known Limitations — NeoSynaptex

> **Purpose.** Every honest research project has a limitations section
> *before* submission. This is ours. Every item listed below is a
> known weakness of the current state of the evidence. None of them is
> buried in a supplementary appendix; they are all first-class facts
> that a reviewer should hold against the headline claim.
>
> Items are ranked by severity:
>
> - **S1 (blocker):** must be addressed before peer-review submission.
> - **S2 (caveat):** must be disclosed prominently in the manuscript.
> - **S3 (improvement):** should be fixed in the next release.

---

## S2 caveats — must be disclosed in manuscript

### L1. Small T1 sample sizes

The four T1 wild-empirical substrates carry 10–20 subjects each:

| Substrate | n subjects | Epochs / beats |
|-----------|-----------:|----------------|
| eeg_physionet (FOOOF) | 20 | ≈ 400 epochs |
| eeg_resting (Welch+Theilsen) | 10 | 299 epochs |
| hrv_physionet (VLF PSD) | 10 | N/A (54 available in full NSR2DB) |
| hrv_fantasia (DFA α₂) | 10 | ≈ 72 000 beats total |

**Impact.** Confidence intervals on each individual T1 entry are
visibly wide (±0.1–0.25 on the γ point estimate). The replication
strategy is to add more subjects per substrate, not to add more
substrates. NSR2DB has 44 more young/adult records; PhysioNet EEGBCI
has 89 more subjects; TUH EEG Corpus would provide > 10 000.

**Mitigation roadmap:**
- Scale eeg_physionet to 50 subjects (same pipeline, no tuning)
- Scale hrv_fantasia to all 20 (10 young + 10 elderly); expect γ to
  drop with age — that itself is a publishable finding.

### L2. eeg_resting lands slightly above the metastable window

The Welch+Theil-Sen resting-state estimate reports γ = 1.255,
CI95 [1.032, 1.452]. The NFI metastable window is [0.7, 1.3].

**Two observations:**

1. The existing eeg_physionet (FOOOF / specparam) on motor-imagery
   runs from the same dataset reports γ = 1.068 — well inside the
   window. The two numbers disagree but both CIs touch the 1/f
   reference 1.0 at their lower bound.
2. The literature gives α ∈ [0.8, 1.8] for eyes-open resting EEG
   across labs and methods (Donoghue 2020, He 2014, Miller 2012).
   γ = 1.26 is consistent with that band.

**Impact.** The `test_gamma_finite_and_in_physical_band` assertion
uses the broader [0.7, 2.0] physiological band for eeg_resting, not
the stricter metastable [0.7, 1.3]. This is flagged in the test
docstring and recorded in `evidence/gamma_provenance.md`.

**Why this is disclosed, not hidden:** the whole point of the
provenance taxonomy is to be honest about when the signal is strong
and when it is marginal. Tuning the alpha-exclusion window or the
frequency range to force γ < 1.3 would be exactly the kind of
fitting-to-window we explicitly reject.

### L3. serotonergic_kuramoto is a calibrated T5 substrate with a 1.17× basin

The serotonergic_kuramoto substrate requires a calibration of the
operational frequency bandwidth σ_op for the γ ≈ 1 claim to hold.

- Reference σ_op = 0.065 Hz
- Basin of γ ∈ [0.7, 1.3]: σ_op ∈ [0.058, 0.068] Hz
- Basin width: 0.010 Hz (σ_max / σ_min ≈ 1.17)
- Bootstrap CI on γ at reference σ_op: [0.145, 1.506] — very wide

**Impact.** A 1.17× basin is modest. A reviewer can reasonably argue
that the serotonergic substrate is *consistent with* γ ≈ 1 in a narrow
regime rather than *evidence for* it. We agree, and that is exactly
the T5 classification in `evidence/gamma_provenance.md`. The
substrate contributes to the T5 all-tier count but not to the T1–T3
headline.

**Reproduction:** `pytest tests/test_calibration_robustness.py -v -s`
sweeps σ_op across [0.054, 0.074] Hz and records the basin width.
Documented in `substrates/serotonergic_kuramoto/CALIBRATION.md`.

### L4. bn_syn R² is 0.28

The critical-branching substrate `bn_syn` reports γ = 0.946 with
R² = 0.28. Every other T3 substrate has R² > 0.8.

**Impact.** The γ point estimate is near 1, but the log-log fit is
noisy. This is a disclosed, not hidden, weakness — the ledger records
R² = 0.28 directly, and `evidence/gamma_provenance.md` lists it under
the bn_syn entry as a known caveat.

**Mitigation:** ongoing work to increase branching-network size and
run length to tighten the fit. The substrate is retained because the
γ point estimate is independently consistent with the other T3
witnesses, and removing it would be cherry-picking.

### L5. zebrafish_wt is T2 (reanalysis), not T1

The zebrafish entry uses the McGuirl 2020 published `.mat` file,
which is itself simulation output from an agent-based model. It is
not raw biological imaging. We classify it as T2, not T1.

**Impact.** Counting zebrafish as wild empirical would overclaim.
It is a useful independent witness precisely because we did not tune
its parameters — the γ comes out of an unrelated paper’s model — but
it is one step less strong than the T1 physiological entries.

### L6. T4 live orchestrator entries are excluded from counts

Two ledger entries (`nfi_unified`, `cns_ai_loop`) have γ values
computed by the NeoSynaptex engine on its own orchestration trace.
Both are marked `tier: "illustrative"` / `status: PENDING_REAL_DATA`
and are **not counted** in the headline T1…T3 witness tallies.

**Impact.** They appear in the ledger for infrastructure testing
purposes but contribute zero epistemic weight to the headline claim.
This is visible in every count row of `evidence/gamma_provenance.md`.

### L7. `cfp_diy` reports γ = 1.83 (out-of-regime)

The Cognitive Field Protocol ABM substrate gives γ = 1.832, CI95
[1.638, 1.978] — well outside the metastable window.

**Why this is a feature, not a bug.** The substrate is retained in
the ledger as an *out-of-regime witness*: a scenario where the γ
machinery works correctly (tight CI, R² = 0.85) but the system itself
is not critical. It demonstrates that γ ≈ 1 is a property substrates
either have or do not, not a fixed-point of the fit.

**How this is surfaced:** `evidence/gamma_provenance.md` lists it as
T3† out-of-regime. The headline "γ ≈ 1 across N substrates" explicitly
*excludes* it from every row except the dedicated falsifying-witness
row.

---

## S3 improvements — next release

### L8. No cross-population replication yet

T1 substrates use the same demographic twice: eeg_physionet and
eeg_resting both use PhysioNet EEGBCI subjects; hrv_physionet and
hrv_fantasia use different databases but both cardiac. There is no
independent lab replication.

**Mitigation:** active outreach for cortex/TUH EEG, BIDMC MIT-BIH,
HCP fMRI. Tracked separately; not a prerequisite for first submission.

### L9. `r2` in bootstrap_metadata is between-unit variance, not regression R²

For per-unit γ populations (EEG subjects, HRV subjects, serotonergic
sweep points), the "R²" reported in the ledger is defined as
`1 − SS_resid/SS_total` around the null γ = 1, not a regression R².
This is documented in `core/bootstrap.py::bootstrap_summary` but the
field name `r2` is ambiguous with `core/gamma.py::compute_gamma.r2`
which IS a regression R².

**Mitigation:** rename to `r2_between_unit` in a schema v2 bump.
Deferred to avoid breaking existing ledger consumers.

### L10. Docker image is validated only in CI, not on the dev machine

The `Dockerfile.reproduce` image is built and smoke-tested on every
relevant push by `.github/workflows/docker-reproduce.yml`. It has
never been successfully built on a developer laptop inside this
repo, because the local Docker daemon was not available during
development. This is visible in the commit history — the image
passed CI but was not runtime-tested locally.

**Mitigation:** once the dev machine has a running daemon, add a
`make docker-repro` target and document expected runtime.

### L11. Optional dev dependencies (mne, specparam, wfdb) are not in pyproject extras

The Dockerfile installs them explicitly because they are large and
only needed for the T1 empirical substrates. In `pyproject.toml` they
are absent from the `dev` extras, which means a plain
`pip install -e ".[dev]"` will not enable the empirical substrates.

**Mitigation:** add an `empirical` extra in `pyproject.toml` that
pulls mne, specparam, wfdb. Tests will still skip gracefully when
missing.

### L12. Manuscript claims automation coverage

`scripts/verify_manuscript_claims.py` checks 20 claims. New ledger
entries (eeg_resting, hrv_fantasia, serotonergic_kuramoto) should be
added to the claim list once they make it into the manuscript body.

**Mitigation:** tracked in `docs/MANUSCRIPT_UPDATES.md` (created as
part of this protocol’s autonomous-decision rule #8).

---

## S1 blockers — open questions with no current resolution

*None at this time.* Every S1 item from the pre-IMMACULATE audit has
been addressed or downgraded to S2/S3. If a reviewer finds an S1
that we missed, that is exactly the kind of thing this document
exists to surface.

---

## How to contest anything here

If a reviewer disagrees with any tier classification, falsification
condition, or S-rank:

1. Open an issue with the specific claim and the evidence.
2. The burden of defence is on us, not on the reviewer.
3. Ledger entries are `locked: true` only to prevent accidental drift;
   they can always be downgraded by an explicit commit with the
   reviewer-supplied evidence.

---

**Last audit:** 2026-04-05. See `evidence/PREREG.md` for the commit
hashes that fix each substrate’s adapter code relative to its measured
γ value.
