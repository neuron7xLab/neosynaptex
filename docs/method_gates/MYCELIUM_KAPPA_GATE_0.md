# Mycelium κ — Method Gate 0 (alt target)

> **claim_status: derived** — alternate-target Gate 0 record. Sister doc to `MYCELIUM_GAMMA_GATE_0.md`. Establishes that **fungal κ** (branching-criticality on hyphal recordings) is a distinct observable from γ, with its **own** falsifiability matrix and its **own** verdict. This document does not run any analysis; it only opens or refuses the gate.

> **Verdict:** `BLOCKED_BY_METHOD_DEFINITION` (current state, two of six rows are FAIL on the strict reading; rationale in §4).

## 1. Why a separate κ gate

The architectural rule (`docs/architecture/recursive_claim_refinement.md` §10) is that every substrate-target pair enters Gate 0 independently. Mycelium has at least two distinct candidate observables:

- **γ** (metastability scaling exponent) — `MYCELIUM_GAMMA_GATE_0.md` Gate 0 = `BLOCKED_BY_METHOD_DEFINITION` on six FAILs.
- **κ** (branching-criticality, the BN-Syn local proxy) — this document.

Conflating these is exactly the κ ≠ γ failure mode the architecture prevents. Each observable gets its own gate, its own falsifiability matrix, its own verdict.

## 2. NeoSynaptex κ definition (recap)

`κ` is the per-step branching ratio of an event chain (the "σ" of branching processes). Critical value `κ ≈ 1` corresponds to a critical branching process where each event triggers, on average, exactly one descendant event.

Operational measurement chain on neuronal-class data (BN-Syn precedent):

1. Discrete event series (spikes / threshold crossings / activity bins).
2. For each non-empty time-bin t, count active units `n_t`.
3. κ̂ = mean over `t : n_t > 0` of `n_{t+1} / n_t`.
4. Surrogate / proxy null rejection (avalanche-fit verdict + p-value floor).
5. Provenance + determinism gates.

Critical regime: `κ̂ ∈ [1 − τ, 1 + τ]` for a small tolerance τ; outside that band the verdict downgrades.

Each step requires the substrate to expose: (i) discrete events on a defensible timescale, (ii) a meaningful "next event" lineage, (iii) replay-deterministic recording, (iv) a falsifiable null distribution.

## 3. Falsifiability test for fungal κ

The same six-row matrix as the γ gate, **specialised for κ-class observables**.

| # | Required property                                                                          | Status on fungal electrophysiology                                                                                                                                                                  | Verdict   |
|---|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| 1 | Identifiable discrete events with a defensible timescale                                   | Hyphal extracellular recordings show "spike-like" events (Adamatzky 2022, Olsson & Hansson 1995) at slow timescales (seconds–minutes). The events exist; their exact thresholding convention is **not** universal but multiple labs report consistent qualitative patterns. | **PARTIAL** |
| 2 | A defensible "next event" lineage / cascade structure                                      | No anatomical primitive analogous to a synaptic cascade has been published on mycelial networks. Hyphal coupling exists, but event-to-event causal chains are not formally characterised in peer-reviewed literature. | **FAIL**    |
| 3 | A reproducible κ̂ pipeline on substrate-native data                                        | Avalanche-style binning + branching-ratio estimators (Beggs–Plenz, Cocchi & Gollo) can be applied mechanically to fungal spike-train surrogates, but no published κ̂ pipeline exists for fungi at NeoSynaptex rigour.                                                                  | **PARTIAL** |
| 4 | A defensible critical regime / band                                                        | The `κ ≈ 1` band is a generic feature of branching processes; specialising it to fungi is a method-definition step. No peer-reviewed fungal κ critical-band study exists with surrogate rejection at the level of BN-Syn.                                                | **FAIL**    |
| 5 | Replay-deterministic recording protocol                                                    | Live biology + environmental confounds (humidity, temperature, light, substrate moisture, age) dominate. Post-hoc deterministic replay on saved raw data is feasible (~70%); biological replay-identical is not (~5%).                                                              | **PARTIAL** |
| 6 | A falsifiable null distribution distinguishing κ-class branching from coloured noise       | Standard nulls (phase-randomised, AAFT, IAAFT, time-shuffle) are mechanically applicable. No published null-control bundle for fungal branching specifically, but the methodology is mature in adjacent fields and portable.                                                | **PARTIAL** |

**Tally: 0 PASS, 4 PARTIAL, 2 FAIL.**

A single FAIL on rows 2 or 4 is sufficient to keep Gate 0 closed under the strict reading: row 2 (no peer-reviewed cascade primitive) and row 4 (no peer-reviewed critical band) are **definitional gaps**, not engineering gaps. Until at least these two flip to PASS or are explicitly downgraded to a documented PARTIAL with a published method-definition paper, κ-on-fungi cannot enter the canonical claim ladder above `NO_ADMISSIBLE_CLAIM`.

## 4. Why κ-on-fungi is closer than γ-on-fungi

Compared to `MYCELIUM_GAMMA_GATE_0.md` (six FAILs), the κ gate has four PARTIALs and two FAILs. The improvement is structural, not motivational:

- κ is an event-chain statistic; fungal recordings expose discrete events. The γ chain requires phase-coupled oscillators, which fungal recordings do not expose.
- κ has a generic critical band (`≈ 1`) that does not depend on substrate identity in the same definitional sense as γ ≈ 1.0 does in NeoSynaptex.
- Standard avalanche-fit + branching-ratio pipelines are portable across substrates; γ pipelines are specific to phase-coupling structure.

This does not mean fungal κ is "almost validated". It means the **bottleneck axes are different**: for γ, six axes are FAIL; for κ, two axes are FAIL and four are PARTIAL. The substrate-readiness number (~30–40% for κ-class fungal study, when peer-reviewed cascade + critical-band rows flip) is qualitatively different from γ-readiness (~5–8%).

## 5. Gate 0 verdict

```
BLOCKED_BY_METHOD_DEFINITION
```

Reasons (machine-readable):

- `KAPPA_CASCADE_PRIMITIVE_UNDEFINED` — §3 row 2: no peer-reviewed event-to-event cascade structure on hyphal networks.
- `KAPPA_CRITICAL_BAND_NOT_PUBLISHED` — §3 row 4: no peer-reviewed fungal critical-band study at NeoSynaptex rigour.

Documented partials (not blockers but also not unblockers; recorded for traceability):

- `KAPPA_EVENT_THRESHOLD_NOT_CANONICAL` — §3 row 1.
- `KAPPA_PIPELINE_NOT_PUBLISHED_FOR_FUNGI` — §3 row 3.
- `REPLAY_DETERMINISM_PARTIAL` — §3 row 5.
- `NULL_DISTRIBUTION_PORTABLE_NOT_PUBLISHED` — §3 row 6.

## 6. Consequence

While this gate verdict stands:

- **No fungal κ data is admitted** into the NeoSynaptex evidence ledger.
- **No fungal κ adapter is wired** into the canonical importer.
- **No fungal κ claim** ("fungal κ ≈ 1", "mycelial criticality at κ", "scale-free fungal branching", etc.) is admissible.
- A publication or preprint that claims "fungal κ ≈ 1" is treated as `ARTIFACT_SUSPECTED` until rows §3.2 and §3.4 flip to PASS with peer-reviewed evidence and surrogate rejection.
- κ ≠ γ remains the global invariant: even if fungal κ becomes admissible, it does **not** project to fungal γ. They are independent gates.

## 7. How fungal κ Gate 0 can be unblocked

Two FAILs and four PARTIALs need to be converted to PASS through peer-reviewed evidence. The minimum-cost unblock path is:

1. **§3.2 (cascade primitive):** a peer-reviewed paper proposing and validating an event-to-event cascade structure on hyphal recordings, with a defensible "parent → descendant" mapping in either electrical or chemical signal propagation. Effort: 1–3 years of collaboration with mycelial electrophysiology lab.
2. **§3.4 (critical-band study):** a peer-reviewed fungal κ̂ + surrogate-rejection study showing a critical regime. Builds on §3.2. Effort: ~12 months once §3.2 lands.
3. PARTIALs §3.1 / §3.3 / §3.5 / §3.6: convertible to PASS through engineering work on a pre-registered protocol with public manifests and standard null pipelines (AAFT/IAAFT/phase-randomised). Effort: ~4–8 weeks once hardware is procured.

Until §3.2 and §3.4 flip, fungal κ stays at `NO_ADMISSIBLE_CLAIM`.

## 8. Non-claims

This document explicitly does **not**:

- claim that fungal κ exists.
- claim that fungal κ does not exist.
- claim that fungi are critical or non-critical.
- promote any fungal observable to a higher ladder state.
- modify the γ-gate verdict (`MYCELIUM_GAMMA_GATE_0.md` remains BLOCKED on six FAILs).
- modify any code, contract, threshold, or pipeline.
- imply that κ-on-fungi is "easier" than γ-on-fungi in a scientific sense; it only reflects that the falsifiability matrix has different bottlenecks.

## 9. Provenance

- Architecture: `docs/architecture/recursive_claim_refinement.md` §2 (claim ladder), §10 (integration rule).
- κ ≠ γ invariant: `docs/claim_boundaries/BN_SYN_LOCAL_STRUCTURAL_EVIDENCE.md`.
- Sister gate: `docs/method_gates/MYCELIUM_GAMMA_GATE_0.md` (γ; BLOCKED on six FAILs).
- BN-Syn precedent for κ pipeline: `contracts/bnsyn_structural_evidence.py`, `tools/import_bnsyn_structural_evidence.py`.
- Future code-level twin: `contracts/mycelium_pre_admission.py` (PR #154); will gain a `MYCELIUM_KAPPA_GATE_ZERO_*` tuple-pair only when Gate 0 unblocks.

---

*This file is a method-definition record only. It admits no fungal data. It will be revisited when peer-reviewed evidence flips §3.2 or §3.4.*
