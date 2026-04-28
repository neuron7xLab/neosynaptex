# BN-Syn → NeoSynaptex: Local Structural Evidence Boundary

This document fixes the boundary of what BN-Syn contributes to
NeoSynaptex when imported via the `tools/import_bnsyn_structural_evidence.py`
pipeline. The integration is **strictly local and structural**.

## What BN-Syn contributes (three metric families)

1. **Branching-ratio surrogate κ.** Drawn from
   `criticality_report.json:sigma_mean`. At criticality the network
   targets `κ ≈ 1.0`. BN-Syn does not currently emit a κ confidence
   interval; the importer therefore accepts a tight point estimate
   *or* a CI overlapping 1.0, never both required, never both
   fabricated.
2. **Avalanche distribution + power-law fit quality.** Drawn from
   `avalanche_report.json` (sizes, durations, counts) and
   `avalanche_fit_report.json` (alpha, p-value, validity verdict).
3. **Phase-coherence summary.** Drawn from
   `phase_space_report.json:coherence_mean`.

Provenance and determinism are lifted from `run_manifest.json`
(artifact hash dict) and `robustness_report.json:replay_check.identical`.

## What BN-Syn does NOT prove (five explicit non-claims)

1. **BN-Syn does not prove γ ≈ 1.0.** κ is a branching-ratio surrogate
   on a single substrate; it is not the cross-substrate γ that
   NeoSynaptex's main pipeline computes from (topo, cost) pairs.
2. **BN-Syn does not prove cross-substrate universality.** A clean
   power-law on one synthetic critical-branching network is consistent
   with mean-field directed percolation; it does not by itself
   establish that any other substrate sits in the same universality
   class.
3. **BN-Syn does not prove emergence of any cognitive property.**
   Avalanche statistics + phase coherence are descriptive structural
   metrics; they do not license claims about consciousness,
   awareness, or general intelligence.
4. **The "phase-surrogate-rejected" flag is a proxy.** BN-Syn does
   not currently emit a phase-randomized null on the coherence trace.
   The importer derives the flag from the avalanche power-law-fit
   verdict (`validity.verdict == "PASS"` AND `p_value` ≥ floor); if
   the proxy is disabled or the fit fails, the flag stays False and
   the verdict downgrades to `ARTIFACT_SUSPECTED`.
5. **The importer never emits `VALIDATED_SUBSTRATE_EVIDENCE` on its
   own.** That verdict requires a γ-side pass supplied by the caller
   (NeoSynaptex's own null-control / provenance / determinism gates).
   The best honest verdict reachable from a BN-Syn bundle alone is
   `LOCAL_STRUCTURAL_EVIDENCE_ONLY`.

## Verdict ladder (fail-closed)

| claim_status                       | meaning                                                                |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `NO_ADMISSIBLE_CLAIM`              | required metric missing / NaN / inf, or local pass fails               |
| `ARTIFACT_SUSPECTED`               | surrogate-rejection flag is False                                      |
| `LOCAL_STRUCTURAL_EVIDENCE_ONLY`   | local pass holds; γ-side judgement absent or absent provenance         |
| `VALIDATED_SUBSTRATE_EVIDENCE`     | local pass + γ-pass + provenance + determinism — only via caller       |

Every claim that surfaces in NeoSynaptex from this channel must
additionally pass NeoSynaptex's own null-control, provenance,
determinism, and downgrade gates. The BN-Syn surface is one input to
that pipeline, not a substitute for it.
