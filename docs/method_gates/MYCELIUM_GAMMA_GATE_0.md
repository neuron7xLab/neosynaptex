# Mycelium γ — Method Gate 0

> **claim_status: derived** — this document is the formal Gate 0 method-definition record for any future mycelial / fungal-electrophysiology substrate. It admits no fungal data, makes no scientific claim, and produces only an architectural verdict.

> **Verdict:** `BLOCKED_BY_METHOD_DEFINITION`

## 1. Gate purpose

Per the recursive claim refinement architecture (`docs/architecture/recursive_claim_refinement.md` §10), every new substrate must enter through Gate 0 *before* a single byte of data is admitted into the evidence ledger. Gate 0 asks one question and one only:

> Can the substrate's intended observables be honestly defined within NeoSynaptex's existing measurement spaces?

If the answer is no, the substrate enters at `BLOCKED_BY_METHOD_DEFINITION`. No data is collected, no contract is wired, no claim status above `NO_ADMISSIBLE_CLAIM` is reachable.

## 2. Substrate under examination

- **Substrate:** mycelium / fungal electrophysiology (extracellular potential recordings on hyphal networks; commonly *Pleurotus*, *Schizophyllum*, *Ganoderma*, *Cordyceps*).
- **Intended target:** the γ observable as authored by NeoSynaptex (metastability scaling exponent, critical value `γ ≈ 1.0`).
- **Question this gate answers:** does fungal electrophysiology admit a γ measurement chain compatible with the NeoSynaptex γ-pipeline?

## 3. NeoSynaptex γ definition (recap)

`γ` in NeoSynaptex is **not** a free-floating exponent. It is the metastability scaling exponent obtained from a specific measurement chain:

1. a population of phase-coupled oscillators (or operationally equivalent neural-mass/Kuramoto-class proxies);
2. a measurable Kuramoto order parameter `R(t) = | (1/N) Σ exp(i φ_k(t)) |`;
3. a metastability scalar `M = Var_t[R(t)]` (or a documented equivalent);
4. a scaling relation between `M` (or its dispersion) and a network-level control parameter, fitted as `~ x^γ`;
5. a critical regime in which `γ ≈ 1.0` is interpretable as scale-free metastability.

Each step requires the underlying substrate to expose: (i) identifiable oscillatory units with phase, (ii) a population-level coupling structure, (iii) replay-deterministic recording, (iv) a falsifiable null distribution.

## 4. Falsifiability test for fungal γ

For γ to be definable on fungal electrophysiology, **all six** of the following must hold. Each row is a falsification test: a single FAIL marks the gate BLOCKED.

| # | Required property                                                                 | Status on fungal electrophysiology                                                                                                                  | Falsification verdict |
|---|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|
| 1 | Identifiable oscillatory units with a well-defined instantaneous phase φ_k(t)     | Hyphal extracellular potentials show slow, irregular, non-stationary fluctuations and bursty "spike-like" events; no canonical oscillator unit, no agreed phase definition. | **FAIL**              |
| 2 | A defensible Kuramoto-class coupling structure between units                       | No anatomical or electrical primitive analogous to a synapse; coupling, if any, is conducted through hyphal continuity and ionic gradients with unclear topology. | **FAIL**              |
| 3 | A reproducible Kuramoto order parameter R(t) on substrate-native data             | No population convention exists; ad-hoc bandpass + Hilbert phase reconstructions are not falsifiable as Kuramoto phases on this substrate.          | **FAIL**              |
| 4 | A defensible metastability scalar with a published critical regime                | No fungal-electrophysiology paper offers a peer-reviewed γ-class metastability fit with surrogate-based null rejection at the same definitional rigor as the NeoSynaptex γ-pipeline. | **FAIL**              |
| 5 | Replay-deterministic recording protocol                                            | Most published mycelial recordings depend on environmental conditioning (humidity, substrate moisture, temperature, light) that is not part of any published deterministic-replay protocol. | **FAIL**              |
| 6 | A falsifiable null distribution distinguishing γ-class scaling from coloured noise | The reported "spike-like" mycelial activity overlaps with low-frequency 1/f-type noise; no canonical null exists that rules this out at NeoSynaptex's gate level. | **FAIL**              |

**Six FAILs out of six required passes.** No subset of fungal electrophysiology, as currently published, satisfies the γ-definition chain.

## 5. Gate 0 verdict

```
BLOCKED_BY_METHOD_DEFINITION
```

Reasons (machine-readable):

- `OBSERVABLE_NOT_DEFINED` — no canonical oscillator/phase definition for fungal hyphae.
- `COUPLING_TOPOLOGY_UNDEFINED` — no peer-reviewed Kuramoto-class coupling primitive.
- `ORDER_PARAMETER_NOT_DERIVABLE` — Kuramoto R(t) cannot be honestly computed.
- `METASTABILITY_SCALAR_NOT_PUBLISHED` — no peer-reviewed fungal γ measurement chain.
- `REPLAY_DETERMINISM_ABSENT` — environmental confounds dominate, no replay-identical protocol.
- `NULL_DISTRIBUTION_ABSENT` — no canonical null to separate γ-class scaling from 1/f noise.

## 6. Consequence

While this gate verdict stands:

- **No fungal data is admitted** into the NeoSynaptex evidence ledger.
- **No fungal substrate adapter is wired** into the canonical importer.
- **No γ claim of any flavour** ("fungal γ ≈ 1", "mycelial criticality", "scale-free fungal metastability", etc.) is admissible.
- **No κ→γ projection** from mycelial branching observables to the γ-claim surface is performed (κ ≠ γ remains the global invariant).
- A publication or preprint that claims "γ ≈ 1 in fungal networks" is treated as `ARTIFACT_SUSPECTED` until the six rows in §4 each turn into PASS with full evidence and surrogate rejection.

## 7. How Gate 0 can be unblocked (future work, not this PR)

Gate 0 will admit a fungal substrate only when **each** §4 row turns into PASS through independent, peer-reviewed evidence chains:

1. A peer-reviewed definition of the unit oscillator and its instantaneous phase on hyphal recordings.
2. A defensible, peer-reviewed coupling primitive (anatomical, electrical, or chemical) that can carry phase information in a Kuramoto-class sense.
3. A reproducible R(t) computation pipeline with code, seed, and surrogate rejection at p < 0.01.
4. A peer-reviewed metastability scalar with a published critical regime and at least two independent replications.
5. A documented replay-deterministic recording protocol with environmental controls and a public manifest.
6. A peer-reviewed null-control distribution distinguishing γ-class scaling from coloured / pink noise.

Until all six are met, Gate 0 stays `BLOCKED_BY_METHOD_DEFINITION` and no Gate 1 (data admission) is opened.

## 8. Non-claims

This document explicitly does **not**:

- claim that fungi are not critical;
- claim that fungi do not have rich electrophysiology;
- claim that γ is impossible to define on fungal substrates;
- claim that mycelial computation is uninteresting;
- promote any claim above `NO_ADMISSIBLE_CLAIM`;
- modify any existing gate, contract, threshold, or pipeline.

It records a **method-definition refusal**: until γ-on-fungi is published with the same rigour as γ-on-NeoSynaptex, the substrate cannot honestly enter the recursive claim ladder. Refusing to measure something that has not been defined is a positive epistemic act.

## 9. Provenance

- Gate sequence: `docs/architecture/recursive_claim_refinement.md` §10 (integration rule).
- Global invariant: `κ ≠ γ` (`docs/claim_boundaries/BN_SYN_LOCAL_STRUCTURAL_EVIDENCE.md`).
- Evidence-ledger contract: `contracts/bnsyn_structural_evidence.py` (template for any future fungal contract once Gate 0 unblocks).
- Strict-JSON output policy: `tools/import_bnsyn_structural_evidence.strict_json_sanitize`, `allow_nan=False`.

---

*This file is the only mycelial artefact in the repository. It is intentionally docs-only. It will be revisited only when peer-reviewed evidence makes any §4 row flip to PASS.*
