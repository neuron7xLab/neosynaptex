# IAAFT Canonical Repair Report (v3.2.0 protocol execution)

> **Date.** 2026-04-15.
> **Protocol.** Post-falsification IAAFT repair (SYSTEM ROLE: principal
> research software engineer & falsification-protocol maintainer).
> **Final verdict.** **IAAFT_NOT_REPAIRED** — under the strict numerical
> gates specified in the protocol (T3 log-Welch-PSD RMSE < 1e-2,
> T5 convergence σ < 5e-3 + per-seed < 1e-2, T8 cascade sep > +0.05),
> the requalification audit still reports FAIL. The canonical
> implementation is however **structurally complete** (single path,
> T4 exact, no drift duplicates). Calibration was NOT rerun per
> Phase-6 gating.

## 1. Root-cause note (Phase 1 audit)

**Pre-repair state.** Three behaviourally independent scalar IAAFT
implementations existed in the main-branch repository:

| # | Location | Loop order | Terminal step | Default iters | Usage |
|---|---|---|---|---|---|
| 1 | `core/iaaft.py::iaaft_surrogate` | spec → amp | amp-remap ✓ | 500 | `core/falsification.py`, `scripts/generate_surrogate_evidence.py`, `tests/test_iaaft.py` |
| 2 | `core/coherence.py::_iaaft_surrogate` | spec → amp | amp-remap ✓ | **10** (too few) | transfer-entropy significance |
| 3 | `contracts/truth_criterion.py::iaaft_surrogate` | spec → amp | amp-remap ✓ | 50 | truth-criterion surrogate test |
| 4 | `run_eegbci_dh_replication.py::iaaft_surrogate` | amp → spec | **spec-match ✗** | 20 | **broken — used in PR #124** and in all the V1 diagnostic/audit scripts via transitive import |

SIGN-FLIP-DIAG-v1 (commit `627bf70`) imported `iaaft_surrogate` from
`run_eegbci_dh_replication` (the #4 broken path) through
`run_sign_flip_diag_v1.py` and `run_calibration_diagnostic.py`. That is
the reason the audit reported T3 RMSE = 0.22 and T4 KS p < 10⁻¹²: the
final state of the surrogate was a spectrum-projected signal whose
amplitude distribution had been re-Gaussianised by the final inverse
FFT, and whose Welch PSD differed from the original because the PSD is
actually estimated on the (shifted) amplitude-matched reconstruction
that never happens in the #4 loop.

**Canonicalisation decision.** `core/iaaft.py` is the single
authoritative scalar implementation. All other call sites now route
through it (wrappers in `core/coherence.py`, `contracts/truth_criterion.py`,
`run_eegbci_dh_replication.py`).

## 2. Patch summary (Phase 2 + 3)

| File | Change |
|---|---|
| `core/iaaft.py` | Rewrote `iaaft_surrogate` with canonical-contract keyword API (`seed`, `n_iter`, `tol_psd`, `stagnation_window`, `timeout_s`, `return_diagnostics`). Added `IAAFTDiagnostics` dataclass, `log_psd_rmse` helper, `stable_rank_remap` helper. Legacy 3-tuple return preserved when caller passes `rng=`. Terminal step is ALWAYS amplitude rank-remap — T4 exact by construction. |
| `core/coherence.py` | `_iaaft_surrogate(x, rng, n_iter=10)` now a 3-line wrapper delegating to `core.iaaft.iaaft_surrogate`. Default `n_iter` lifted 10 → 200. |
| `contracts/truth_criterion.py` | `iaaft_surrogate(series, rng)` now a wrapper delegating to the canonical path. |
| `run_eegbci_dh_replication.py` | Broken in-file IAAFT replaced by a wrapper `iaaft_surrogate(signal, seed, n_iter)` delegating to canonical. PR #124 numerical artefact is preserved on disk; any re-run must be filed as new evidence. |
| `tests/test_iaaft.py` | Hardened: length preservation, seed determinism, seed variability, T4 exact-sort gate, T3/T5 regression ceilings at 0.05 (documented as protection against re-introduction of the spec-match bug; strict 1e-2 gate lives in the audit runner), convergence diagnostics presence, iteration-sweep stability, cross-seed σ < 5e-3, timeout reporting. 22 cases. |

Duplicate removal: **three** behaviourally-independent IAAFT paths were
redirected to one canonical source. `iaaft_multivariate` and
`kuramoto_iaaft` in `core/iaaft.py` keep their own alternating-
projection loops because they are array-shape-specialised; both also
use terminal amp-remap per channel.

## 3. Exact tests run (Phase 4)

```
pytest tests/test_iaaft.py tests/test_coherence.py -q
    → 33 passed (22 iaaft + 11 coherence)
python run_sign_flip_diag_v1.py
    → requalification audit on real NSR2DB records nsr001..nsr005
```

## 4. Test summary

* `tests/test_iaaft.py` — 22/22 PASS.
  - Legacy back-compat (8) preserved (tuple return, spectral fidelity,
    multivariate shape, cross-correlation destruction, kuramoto shape,
    p-value formula, timeout).
  - Canonical-contract (14) added: T4 exact to 1e-10 at n∈{512, 1024,
    4096, 32768}, seed determinism, cross-seed σ < 5e-3 at n=32k,
    iteration-sweep non-growth, timeout reports
    `terminated_by_timeout`, new-API array return vs legacy-API tuple
    return, T3/T5 regression ceilings at 0.05.
* `tests/test_coherence.py` — 11/11 PASS (coherence remains correct
  after redirection).

## 5. Diagnostic result (Phase 5, on real NSR data)

Re-run of SIGN-FLIP-DIAG-v1 **after** canonicalisation:

| Test | Pre-repair (commit 627bf70) | Post-repair | Change |
|---|---|---|---|
| T1 direction | PASS (file pattern) | FAIL_IMPL_DIRECTION | file still uses `sep = IAAFT − real`; Patch D1 intentionally NOT applied (blocked by rest of audit) |
| T2 Δh definition | PASS | PASS | unchanged |
| **T3 PSD** | FAIL RMSE 0.22 | FAIL RMSE **1.65** | *worse* in log-RMSE: broken path preserved |fft| exactly (only amplitude was wrong), canonical path preserves amplitude exactly (only |fft| drifts). Both fail the 1e-2 gate — the gate is unreachable by alternating-projection IAAFT on rich-PSD signals |
| **T4 amplitude** | FAIL KS p≈0 | **PASS KS p = 1.0** | FIXED. Sort-diff exactly 0.0 on all records. |
| **T5 convergence** | FAIL σ={..., 0.039} | FAIL σ={0.004, 0.016, 0.038, 0.005, 0.073} | σ still exceeds 1e-2 on 3/5 records; IAAFT converges to a signal-dependent plateau that itself varies across records |
| T6 MFDFA params | PASS | PASS | sign invariant |
| T7 preprocessing | PASS | PASS | unchanged |
| **T8 synthetic** | PASS (cascade sep +0.084) | **FAIL_PIPELINE_VALIDITY** (cascade sep **−0.101**) | *New information*. With a correct terminal amp-remap, the binomial p-cascade's Δh is **indistinguishable** from that of its IAAFT surrogate. The T8 "pass" under the broken path was an artefact of the Gaussianising inverse-FFT terminal step destroying the cascade's amplitude distribution. |
| T9 subject distribution | PASS | PASS | unchanged |
| T10 cross-seed | PASS | PASS | σ(sep) < 0.05 across 10 seeds |

Summary:

```
T3  FAIL    T4  PASS    T5  FAIL    T8  FAIL
```

Under the protocol's priority-ordered verdict logic, `FAIL_IAAFT_*`
fails → `IMPLEMENTATION_ERROR`. The repair therefore does **not** clear
the audit.

## 6. Calibration rerun (Phase 6)

**NOT RUN.** Gates T3/T5 must be green on the repaired path before
Phase 6 may execute (INV-CAL-02 equivalent). They are not green.

## 7. Scientific interpretation (protocol-bound)

Until the audit gates are green the sign-flip remains **scientifically
uninterpretable**; that is the protocol-mandated reading.

Three non-protocol observations the user may find useful when deciding
next steps — strictly advisory, not part of any scientific claim from
this repository today:

1. **T3 gate (1e-2 log-Welch-PSD RMSE) is not reachable by
   alternating-projection IAAFT on rich-PSD real HRV data.** The
   canonical implementation converges in ~6 iterations to a plateau of
   log-PSD RMSE ≈ 0.83–0.97 on 54k-sample 4-Hz-resampled NSR records
   regardless of `nperseg ∈ {256, 512, 1024, 2048}`. This is an
   intrinsic property of the algorithm on signals with >10³× PSD
   dynamic range (VLF peak over HF tail). Clearing the 1e-2 gate
   requires either (a) a different surrogate family (e.g. MCMC
   constrained realisations, wavelet surrogates), or (b) a different
   metric that is not log-scale sensitive to low-power bins, or
   (c) a different gate threshold reflecting the achievable floor.

2. **T8 FAIL is a real property of MFDFA+IAAFT, not a bug.** With
   terminal amp-remap, a deterministic p-cascade's singularity
   spectrum Δh is **fully explained** by the cascade's amplitude
   distribution + power spectrum. The surrogate's Δh (0.48) exceeds
   the real cascade's Δh (0.37). This is consistent with the known
   limitation that IAAFT is a valid null ONLY for processes whose
   multifractality is carried by temporal ordering rather than by
   amplitude distribution. For broadband real HRV this caveat is
   probably benign (amplitude distribution is near-Gaussian); for
   deterministic multifractal cascades it is fatal. The user's
   earlier note stands: «це не технічний баг, це наукова інформація
   першого порядку».

3. **T4 is now exact.** The single clear-cut implementation defect
   that this protocol was designed to find (amplitude-distribution
   drift) is fixed. Any future analysis that relies on exact
   amplitude preservation is now sound.

## 8. Artefacts

```
core/iaaft.py                                       (canonical, +150 LOC)
core/coherence.py                                   (wrapper redirect)
contracts/truth_criterion.py                         (wrapper redirect)
run_eegbci_dh_replication.py                         (wrapper redirect)
tests/test_iaaft.py                                  (22 cases, up from 8)
evidence/replications/hrv_iaaft_calibration/
    sign_flip_diag.json                             (requalification audit)
    IAAFT_REPAIR_REPORT.md                          (this file)
```

## 9. Final verdict

```
IAAFT_NOT_REPAIRED
```

Rationale: the canonical path is in place and T4 is exact, but T3, T5,
and T8 still fail the strict protocol gates on real NSR2DB data. Per
the protocol's Phase-6 gating and scientific-interpretation law,
calibration is not rerun and no sign-flip interpretation is carried
forward.

## 10. Next decision (belongs to user)

Three options, each with its own protocol boundary:

* **(A)** Accept the 1e-2 gate as aspirational and adopt a more
  achievable threshold (e.g. 1e-1 or a non-log metric) — this is a
  **threshold tuning** decision that the user explicitly forbade under
  the current protocol and therefore requires a new protocol version.
* **(B)** Keep the 1e-2 gate and change the surrogate family. IAAFT
  alternating-projection cannot meet it on real HRV. Candidates:
  Schreiber 2000 CR (constrained realisations via MCMC), AAFT without
  iteration, wavelet-based surrogates, Gaussian Process bootstrap.
* **(C)** Accept the protocol verdict IAAFT_NOT_REPAIRED and stop the
  MFDFA+IAAFT line of work entirely; revert scope to the between-
  population HRV pathology marker from PR #102 (Cohen's d = 1.85) which
  does not require any IAAFT null.
