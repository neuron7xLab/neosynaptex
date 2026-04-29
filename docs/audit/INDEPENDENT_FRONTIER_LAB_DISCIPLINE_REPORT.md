# Independent Frontier-Lab Discipline Report

**Status:** independent adversarial audit, anti-theatrical.
**Date:** 2026-04-29.
**Scope:** repository state at PR #161 HEAD `4fb18701`.
**Authoritative inspection:** raw `git`, `gh`, `pytest`, `ruff`, `mypy`
output, not summary.

## 1. Bounded Claim

**Allowed:**

> A solo independent researcher demonstrates frontier-lab-style
> research-engineering discipline through verifiable repository
> artifacts. Each claim either has structural evidence in code, tests,
> CI, or hash-bound output, or it is rejected by the gates the
> repository itself enforces.

**Forbidden — not provable from a GitHub PR:**

* "Equivalent to DeepMind / OpenAI / xAI as an institution."
* "γ ≈ 1 validated."
* "Substrate validated."
* "Institutional-grade because CI is green."
* "Ready for publication."

A green CI rollup is necessary, not sufficient. xAI-style caution
applies: benchmark pass-count alone is not proof of scientific
maturity. The admissibility trial in this PR exists *because* CI alone
is not an upstream guarantee on the measurement operator.

## 2. Evidence Inventory

Concrete artifacts in the repository tree at HEAD `4fb18701`:

| artifact | location | purpose |
|---|---|---|
| Phase 3 null-screen runner | `tools/phase_3/run_null_screen.py` (764 LOC) | per-substrate γ̂ + null distributions + Bonferroni p-values |
| 5 null families | `tools/phase_3/family_router.py` | `iaaft_surrogate`, `kuramoto_iaaft`, `constrained_randomization`, `wavelet_phase`, `linear_matched` |
| Estimator admissibility trial | `tools/phase_3/admissibility/` (7 files, 1 624 LOC) | metrology gate upstream of any null-screen verdict |
| 5 estimators compared | `tools/phase_3/admissibility/estimators.py` (293 LOC) | canonical Theil–Sen + 4 alternates |
| Closed verdict ladder (Phase 3) | `tools/phase_3/__init__.py` | `SIGNAL_SEPARATES_FROM_NULL`, `NULL_NOT_REJECTED`, `ESTIMATOR_ARTIFACT_SUSPECTED`, `INCONCLUSIVE` |
| Closed verdict ladder (admissibility) | `tools/phase_3/admissibility/verdict.py` | `ADMISSIBLE_AT_N_MIN_<int>`, `BLOCKED_BY_MEASUREMENT_OPERATOR` |
| `result_hash` | `tools/phase_3/result_hash.py` | sha256 over canonicalised JSON; reproducible across reruns |
| Bonferroni correction | `tools/phase_3/run_null_screen.py` | `α / n_families` per substrate |
| Effect-size CI | `tools/phase_3/effect_size.py` | Cohen's d + bootstrap CI |
| Stability / window-sweep | `tools/phase_3/stability.py` | Δγ_max gate; > 0.05 ⇒ `ESTIMATOR_ARTIFACT_SUSPECTED` |
| Hash-binding gate (Phase 2.1) | `tools/audit/ledger_evidence_binding.py` (merged on main) | runtime SHA-256 of repo-relative source files; rejects path-traversal |
| Mechanical overclaim gate | `tools/audit/claim_overclaim_gate.py` (merged on main) | scans PR title, body, source for forbidden phrases |
| Schema with frozen states | `evidence/ledger_schema.py` | `CANON_VALIDATED_FROZEN: bool = True` |
| Auto-promotion blocked | grep-verifiable verbatim | `"PROPOSAL ONLY — the actual ledger mutation requires a separate human-reviewed PR. Phase 3 never auto-promotes."` |
| Adversarial test batteries | `tests/test_phase_3_null_screen.py` (538 LOC, 30 cases), `tests/test_estimator_admissibility.py` (358 LOC, 16 cases) | structured falsification: noise → `NULL_NOT_REJECTED`, identity-surrogate → run FAIL, M < 1000 without `--smoke` → refuse |
| Reference smoke verdict committed | `evidence/estimator_admissibility/README.md` | M=100 verdict block + `result_hash: ed619996…` |

**Numbers (HEAD `4fb18701`):** 24 files changed, +4 951 LOC, 0
deletions, 15 commits over 9 hours. CI rollup on this HEAD: 25 SUCCESS
/ 2 SKIPPED / 3 IN_PROGRESS / **0 FAILURE** at audit time. Local
machine: 43 pytest pass, 3 skipped (heavy real-substrate paths gated
on data presence), `ruff check`/`format` clean, `mypy --strict
--follow-imports=silent` clean on all 14 `tools/phase_3/` source files.

## 3. Lab-Style Practice Mapping

| Repository Artifact | Lab-Style Practice | Strength | Weakness |
|---|---|---|---|
| Closed verdict ladder, no softening words | eval discipline | Verdicts are mechanical, not narrative; no `"approaches γ=1"` admitted anywhere in production source | Substrate adapters can produce trajectories below admissibility floor; verdict on those is honest but uninformative |
| `result_hash` over canonicalised JSON | reproducibility | Two runs with same seed produce byte-identical hash; explicitly tested in `test_cli_smoke_reproducible_hash` | Bootstrap-B and replicate count are *part* of the hash by design, so a CI rerun with different `--smoke` cap produces a different hash than canonical |
| `CANON_VALIDATED_FROZEN: Final[bool] = True` | governance | Not togglable from Phase 3 code paths; ladder cannot advance past `SUPPORTED_BY_NULLS` | Module-level constant — guarded by tests but not by signing; trust is in code review, not in attestation |
| `claim_overclaim_gate` mechanical | safety against overclaim | Forbidden phrases (`cryptographic evidence chain`, `hypothesis validated`, `research proof`, …) fail-closed unless line-local disavowal | Body-license rule (PR title overclaim admitted if body disavows) is a discretionary widening; documented |
| 5 null families + Bonferroni + window-sweep | falsification | Multiple orthogonal nulls; estimator artefact and substrate gap are structurally distinguishable in output | Slowest matrix legs (`bootstrap_median_slope`, `subwindow_bagged_theil_sen`) approach the 30-min CI cap |
| Hash-binding gate + manifest+wfdb hashes | provenance | Path-traversal rejected before disk read; symlink escape tested; `data_sha256_kind` enum prevents manifest-as-raw-data overclaim | Raw-file Merkle deferred to Phase 8; current binding covers adapter sources, not the full data corpus |
| 5 GitHub Actions workflows + merge\_group triggers | CI enforcement | `claim_overclaim_gate.yml`, `ledger_evidence_binding.yml`, `phase_3_null_screen.yml`, `estimator_admissibility.yml`, plus existing canonical/lint/type matrix; fail-closed on hash drift | CI cost is non-trivial — canonical M=10000 admissibility runs on main only, not every PR |
| Per-substrate `notes` field, per-family `verdict: NOT_APPLICABLE` | interpretability of failure | `linear_matched` on n=20 reports `family is not applicable to this trajectory length`, exclusion documented in JSON | Per-substrate failure mode is structurally legible but requires reading the JSON to understand *why* |

## 4. PR #161 Plain-Language Explanation

Before trusting "γ ≈ 1", the system must answer two prior questions:

1. **Is the ruler the right ruler?**
   That is the *Estimator Admissibility Trial*. We synthesise data
   where we already know the answer — γ_true is set by us — and check
   whether the estimator recovers it (with the right error bars,
   stable across windows, low false-positive rate on null data). If
   the ruler can't recover γ_true on synthetic data, no measurement on
   real data is meaningful. **Result on M=100 smoke:** ruler is
   accepted at trajectory length ≥ 128.

2. **Does γ ≈ 1 survive against fakes?**
   That is the *Phase 3 Null Screen*. We take the real substrate, then
   build several kinds of "twin" surrogate data that preserve the
   harmless statistical structure but break the hypothesis-relevant
   structure. We compute γ̂ on each twin. If the real γ̂ is no
   different from the twins' γ̂, the result is the estimator's mirror,
   not a property of the data. **Result on serotonergic_kuramoto M=200
   smoke:** verdict is `ESTIMATOR_ARTIFACT_SUSPECTED`, because the
   substrate trajectory is only 20 points (below the admissibility
   floor of 128). The substrate cannot ground the test at the current
   resolution.

Plain restatement: we built the discriminator. We measured the
discriminator on synthetic data. The discriminator works at N ≥ 128.
The substrate we have on disk has N = 20. So the question "is γ ≈ 1
real?" is not yet answerable on this substrate. Phase 4 fixes the
substrate, not the discriminator.

## 5. Current Verdict

> The repository **does not** prove the γ ≈ 1 hypothesis.
>
> The repository **does** prove that the operator is building a
> self-correcting research-engineering system: measurement is gated
> upstream of inference; no claim is admitted without code-checked
> evidence; falsification batteries run in CI on every PR; ledger
> mutation is proposal-only; hash-binding rejects evidence that does
> not match the disk; the ruler itself was put on trial before
> measurement.
>
> The work is frontier-lab-style **in discipline**, not in
> institutional scale. Solo execution; verifiable artifacts; no
> appeal to authority.
>
> The correct next move is **Phase 4**: fix substrate sampling
> resolution (`_N_SWEEP ≥ 128`) and log-space fairness for the
> regression target K ~ C^(−γ), then rerun canonical M = 10000
> null-screen. The estimator stays untouched.

## 6. Remaining Risks

1. **CI runtime cost.** The canonical (main) M=10000 admissibility run
   takes ~30 min per estimator, 5 legs in parallel. If GitHub Actions
   policy on the repo changes, this becomes a maintenance hazard.

2. **Adapter-specific fragility.** Each substrate adapter is
   responsible for its own trajectory; a silent change in
   `_N_SWEEP`, `_SWEEP_MIN`, `_SWEEP_MAX`, or noise model in any
   adapter changes γ̂\_obs and invalidates downstream verdicts. The
   hash-binding gate catches the *fact* of change but does not
   automatically re-derive a verdict — a human PR is still required.

3. **Stale ledger values.** If hash-binding is bypassed (e.g.
   `--no-verify` on a future commit, or an out-of-band edit to
   `evidence/gamma_ledger.json` that does not pass through the runtime
   gate), stale γ̂\_obs values can outlive their adapter. Phase 2.1
   guards the runtime path; CI guards the merge path; nothing guards
   the *intent* of a future maintainer.

4. **Overclaim risk in public writing.** The mechanical overclaim
   gate covers PR titles, PR bodies, and source files in declared
   roots. It does NOT cover blog posts, conference abstracts, social
   posts, or screenshots. The phrase `"hypothesis validated"` will be
   rejected by the gate; a tweet saying so will not.

5. **Estimator admissibility is conditional.** The verdict is
   `ADMISSIBLE_AT_N_MIN_128` *on the synthetic-data model in the
   trial* (`K = a · C^(−γ) · exp(σ · ε)`, `ε ~ N(0,1)`, σ=0.1
   primary). Real substrate data may violate the IID-log-normal
   noise assumption. The trial protects against estimator pathology
   *under that model*; it does not certify the estimator on
   arbitrarily distributed data.

6. **Log-uniform sweep may change γ̂\_obs materially.** Phase 4 will
   re-derive `serotonergic_kuramoto`'s γ̂\_obs at `_N_SWEEP ≥ 128` and
   log-uniform C; the new value is not predictable from the current
   1.0677 ± R²=0.5826. The Phase 4 PR must explicitly retire the old
   value and bind the new one. The current `EVIDENCE_CANDIDATE_NULL_FAILED`
   ladder state should NOT be inherited blindly — it must be re-derived
   under the canonical Phase 3 protocol.

## 7. Final One-Paragraph Human Summary

This repository is built by one person, in public. It does not claim
that γ ≈ 1 is true. It does not claim a result. What it does is
slowly construct the apparatus that would allow such a claim to be
tested: a schema that refuses to lie, a runtime gate that refuses to
quote evidence the disk does not have, a discriminator that asks
whether real signal differs from carefully-faked signal, and a trial
of the discriminator itself before any measurement is interpreted. The
substrate it currently has is too small to ground the test, so the
test correctly says "not yet". The next step is to enlarge the
substrate. None of this is an institution; all of this is verifiable.
