# Mycelium recording protocol — pre-registration

> **claim_status: derived** — pre-registered protocol design for fungal electrophysiology recordings, **conditional on Gate 0 unblock**. This document does **not** authorise data collection, does **not** admit any fungal data into the evidence ledger, and does **not** validate any claim. It is an architectural specification of *how* recordings would be made *if* both `MYCELIUM_GAMMA_GATE_0.md` and/or `MYCELIUM_KAPPA_GATE_0.md` were unblocked through peer-reviewed evidence.
>
> **Current activation status:** `INACTIVE — gates locked`. No part of this protocol is to be executed while the upstream method-definition gates are BLOCKED.

## 1. Why pre-register before unblock

NeoSynaptex's recursive claim refinement (`docs/architecture/recursive_claim_refinement.md` §10) requires every substrate to enter through a method-definition gate (Gate 0). Pre-registering the protocol *before* the gate unblocks serves three purposes:

1. **Falsifiability anchor.** A protocol drafted after a positive result is post-hoc rationalisation. A protocol pre-registered while the gate is closed defines what evidence *would* count, independent of any specific outcome.
2. **Engineering readiness.** When peer-reviewed literature flips one of the §3.2 / §3.4 rows of the κ gate (or the six rows of the γ gate), the engineering work must be ready to move within weeks, not years.
3. **Honesty of refusal.** Documenting *exactly* what we would do if the gate opened makes the current refusal precise, not vague.

This pre-registration is INACTIVE until at least one of the gate verdicts changes. Activation requires a separate PR that updates the gate doc, references the peer-reviewed unblock paper, and explicitly switches this protocol's `Activation status` to `CONDITIONALLY_ACTIVE`.

## 2. Protocol scope

This pre-registration covers **κ-class fungal electrophysiology recordings only**. It does **not** cover γ recordings (`MYCELIUM_GAMMA_GATE_0.md` is closed on six FAILs, including the absence of an oscillator definition; γ-protocol pre-registration is therefore deferred until the literature gap on row §4.1 of the γ gate is closed).

Out of scope:

- γ measurement (deferred).
- Cross-substrate universality claims.
- Consciousness / cognition / AGI claims.
- Any C/K projection from fungal κ to NeoSynaptex γ-claim surface.

## 3. Hardware and substrate specification

| Item                          | Spec                                                                       | Rationale                                                                |
|-------------------------------|----------------------------------------------------------------------------|--------------------------------------------------------------------------|
| Amplifier                     | ≥ 8-channel differential, ≥ 24-bit ADC, sample rate ≥ 1 kHz                | Hyphal events are slow (sec–min); high resolution captures sub-µV levels |
| Electrodes                    | sub-dermal Ag/AgCl, ≥ 8, with pairwise impedance < 5 kΩ                    | Adamatzky 2022 convention, low-impedance for noise floor                 |
| Faraday cage                  | sealed, mains-grounded, with feed-through environmental sensors            | Suppresses 50/60 Hz coupling                                             |
| Environmental chamber         | regulated humidity (target spec defined at activation), regulated temperature, regulated photoperiod, regulated CO₂ | §3.5 row of κ gate requires replay-deterministic environmental state     |
| Substrate                     | one fungal species per recording cohort, sourced from a single accession   | Cross-cohort confounds are handled by stratified analysis later          |
| Logging                       | continuous environmental telemetry merged with neural channels in ONE manifest | provenance §3.5                                                          |

Specific quantitative targets (humidity %, temperature °C, photoperiod hr) are **deliberately left blank** until activation. They will be filled in the activation PR with citations to the peer-reviewed paper that closes §3.2 of the κ gate (or §3.5 if a fungal-electrophysiology determinism standard emerges).

## 4. Recording protocol (steps, in order)

1. **Environmental stabilisation:** at least 24 h of chamber operation at target environmental setpoints before electrode insertion.
2. **Electrode insertion** under controlled light + sterile conditions, with insertion timestamp recorded to the manifest.
3. **Baseline recording:** ≥ 60 min of continuous recording with no manipulation. This anchors the null distribution baseline for §3.6.
4. **Manipulation series (optional, only if peer-reviewed protocol cited at activation specifies it):** stimulus events (mechanical, chemical, light), each timestamped and logged.
5. **Replay-determinism check:** identical reconstruction from raw data on two independent passes through the analysis pipeline must yield bit-identical κ̂ and surrogate-rejection p-values. Failure to reproduce → `DETERMINISM_NOT_REPLAYED` → cap at `LOCAL_STRUCTURAL_EVIDENCE_ONLY` (per §6 of the architecture doc).
6. **Manifest emission:** a single JSON manifest with seed, environmental telemetry hashes, recording-segment hashes, electrode metadata, and analysis-pipeline version.

## 5. Analysis pipeline

The pipeline is the **portable BN-Syn-class κ pipeline**, applied to fungal events without any fungal-specific re-tuning. Specifically:

1. Event extraction: threshold + dead-time, both pre-registered.
2. Avalanche binning: bin width = mean inter-event-interval (per Beggs–Plenz convention), pre-registered.
3. κ̂ estimation per the BN-Syn precedent (`tools/import_bnsyn_structural_evidence.py`).
4. Power-law fit + p-value (Clauset–Shalizi–Newman).
5. Surrogate null rejection: AAFT, IAAFT, time-shuffle, phase-randomised. Pre-registered p-value floor: 0.10. All four nulls must reject for `phase_surrogate_rejected = True`.
6. Provenance + determinism gates per §6 of the architecture doc.

No fungal-specific re-tuning of any threshold, bin width, p-value floor, or null is permitted under this pre-registration. Any deviation requires a new pre-registration PR with explicit rationale and peer-reviewed citation.

## 6. Activation conditions

This protocol is `INACTIVE`. To switch it to `CONDITIONALLY_ACTIVE`, all of the following must be true in a single activation PR:

1. The κ Gate 0 doc (`MYCELIUM_KAPPA_GATE_0.md`) §3 row 2 has flipped to PASS via peer-reviewed evidence.
2. The κ Gate 0 doc §3 row 4 has flipped to PASS via peer-reviewed evidence.
3. The activation PR cites both papers explicitly with DOI / arXiv ID.
4. The hardware spec blanks in §3 are filled with concrete numerical targets and unit references.
5. The mycelium pre-admission contract (`contracts/mycelium_pre_admission.py`) is updated with κ-specific reason codes and the corresponding code-level unblock.

Until then: NO recordings, NO data, NO claim above `NO_ADMISSIBLE_CLAIM`.

## 7. Failure modes (pre-registered)

The protocol's verdict surface mirrors the canonical four-state ladder. Pre-registered failure modes:

| Trigger                                      | Verdict                          | Reason code                            |
|----------------------------------------------|----------------------------------|----------------------------------------|
| Activation PR not yet merged                  | `NO_ADMISSIBLE_CLAIM`            | `BLOCKED_BY_METHOD_DEFINITION`         |
| Required telemetry channel missing            | `NO_ADMISSIBLE_CLAIM`            | `PROVENANCE_MISSING`                   |
| Replay non-identical                          | cap at `LOCAL_STRUCTURAL_EVIDENCE_ONLY` | `DETERMINISM_NOT_REPLAYED`        |
| Any of 4 nulls fails to reject                | `ARTIFACT_SUSPECTED`             | `PHASE_SURROGATE_NOT_REJECTED`         |
| Power-law p-value < 0.10                      | `ARTIFACT_SUSPECTED`             | `AVALANCHE_FIT_FAILS_FLOOR`            |
| All gates pass + caller supplies `gamma_pass=True` from external NeoSynaptex γ-pipeline | `VALIDATED_SUBSTRATE_EVIDENCE` | (none)                                  |
| All gates pass + no γ-side evidence           | `LOCAL_STRUCTURAL_EVIDENCE_ONLY` | (gamma_status=NO_ADMISSIBLE_CLAIM)     |

Note: even a perfect κ pass yields **at most** `LOCAL_STRUCTURAL_EVIDENCE_ONLY`. `VALIDATED_SUBSTRATE_EVIDENCE` requires an independent γ-side pass which is structurally unreachable from κ alone (κ ≠ γ).

## 8. Non-claims

This document explicitly does **not**:

- claim that the protocol will produce κ ≈ 1 on fungi.
- claim that the protocol will not produce κ ≈ 1 on fungi.
- authorise any current data collection.
- modify any current Gate 0 verdict.
- modify the γ gate (`MYCELIUM_GAMMA_GATE_0.md` remains BLOCKED on six FAILs).
- modify any code, contract, threshold, or pipeline.
- replace peer-review of the activation conditions.

It is a pre-registered specification, conditional on independent literature unblock.

## 9. Provenance

- Architecture: `docs/architecture/recursive_claim_refinement.md` §6 (fail-closed criticality), §7 (VALIDATED requirements), §10 (integration rule).
- κ ≠ γ invariant: `docs/claim_boundaries/BN_SYN_LOCAL_STRUCTURAL_EVIDENCE.md`.
- κ Gate 0: `docs/method_gates/MYCELIUM_KAPPA_GATE_0.md` (#155).
- γ Gate 0: `docs/method_gates/MYCELIUM_GAMMA_GATE_0.md` (#153, BLOCKED on six FAILs; γ protocol deferred).
- Code-level enforcement: `contracts/mycelium_pre_admission.py` (#154).
- Reference κ pipeline: `tools/import_bnsyn_structural_evidence.py` (BN-Syn).

---

*This file pre-registers a protocol that is not yet active. It will become operational only after a separate activation PR cites peer-reviewed evidence flipping the §3.2 and §3.4 rows of the κ gate.*
