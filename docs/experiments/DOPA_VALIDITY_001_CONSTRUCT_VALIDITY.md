# DOPA-VALIDITY-001 — Construct-Validity Checklist

Each gate is a hard stop. A failed gate yields an INADMISSIBLE verdict, which
is a **success** of the instrument, not a limitation to be softened in prose
(prose de-escalation of an admissibility blocker was itself a flagged #199
failure). Status reflects the seeded reference run on this branch.

| # | Hard gate | Mechanism | Status |
|---|---|---|---|
| 1 | **DNCA signal source exists and is imported** | `load_dopamine_operator()` imports + forward-runs the real `neuron7x_agents…DopamineOperator`; `None` ⇒ `INADMISSIBLE_MISSING_DNCA_EXECUTABLE_SIGNAL` | ✅ executable (torch 2.5.1) |
| 2 | **dopamine/vRPE is signed** | vRPE = pre-asymmetric `valence` = `clamp(δ,−1,1)`; sign preserved, not the ×5.5/×1.0-gained channel | ✅ |
| 3 | **Verifier beats majority AND random** | pure recomputation, deterministic, network-free; `beats_majority ∧ beats_random` else `INADMISSIBLE_WEAK_VERIFIER` | ✅ acc 1.0 > maj ≈0.52 > rand 0.5 |
| 4 | **Signed vRPE truth-correlated (precond. #3)** | Spearman of the **routed** score `−vRPE` vs needs-verify, `p<0.01 ∧ ρ>0`, *before* any routing read; else `INADMISSIBLE_WEAK_VERIFIER` | ✅ ρ=+0.175, p=0.0066 (weak but admissible) |
| 5 | **VCR is not plain accuracy** | VCR = budgeted closure-event rate ≠ policy label accuracy; equality ⇒ `INADMISSIBLE_METRIC_COLLAPSE` | ✅ definition + numeric guard |
| 6 | **Data/input CI-reproducible** | task synthesised from seeded `np.random.default_rng`; `data_hash` over all arrays; no git-ignored corpus | ✅ |
| 7 | **Negative control is real sign inversion** | `dopa_inverted = −dopa`; test rejects any `\|vRPE\|`-complement; must reorder routing | ✅ enforced by test |
| 8 | **Baselines include uncertainty_only and no_vRPE** | 6 policies: `dopa_signed_vrpe, uncertainty_only, no_vRPE, signed_vrpe_inverted, random_gate, verify_all` under equal budget | ✅ defined (only read at Step D) |
| 9 | **Statistical test exists for the delta** | paired Wilcoxon signed-rank over 12 seeds + rank-biserial effect size; pre-registered `ALPHA`, `DELTA_MIN` | ✅ implemented |
| 10 | **Config/code SSOT (no drift)** | every constant in `dopa_validity_001_config.py`; test asserts the experiment defines none | ✅ enforced |
| 11 | **Repro hash binds the conclusion** | `repro_hash = sha256(verdict ‖ all decision inputs)`; test asserts a mutated verdict changes it | ✅ |
| 12 | **No unscoped theory verdict** | a KILL is only `KILL-0979B…`, scoped; test forbids "DOPA-CLOSURE killed" | ✅ enforced |

## Reference-run verdict

`KILLED` (scoped → `KILL-0979B_DNCA_DOPA_ROUTING`). Steps A, B1, B2, C all
genuinely pass: real executable DNCA dopamine signal; verifier 1.0 ≫ baselines;
routed `−vRPE` weakly but admissibly correlated (ρ=+0.175, p=0.0066); VCR ≠
accuracy. At Step D the DNCA signed-vRPE routing **fails**: `dopa ≈ 9.25` vs
`uncertainty_only ≈ 9.17` (Δ=0.002 ≪ DELTA_MIN 0.05), Wilcoxon `p = 0.65`, and
it is **worse than `random_gate ≈ 12.5`**. The true sign-flip control collapses
(`signed_vrpe_inverted ≈ 1.67`), confirming the control is real.

This is a legitimate scoped negative — the *first* admissible DOPA/DNCA
instrument — not a fabricated kill: all seven RETRACTION preconditions hold and
significance was tested. **DOPA-CLOSURE the theory remains UNTESTED**; the kill
binds only this implementation (untrained value-net, arithmetic micro-task).
A prior pre-merge run reported `INADMISSIBLE_WEAK_VERIFIER` due to a B2 sign
bug (review P1, amendment A1) that produced a *false* INADMISSIBLE; correcting
the gate's sign — not any threshold — surfaced this honest scoped KILL.
