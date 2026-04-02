# NeoSynaptex Manuscript Skeleton

## 1. Introduction
This section defines the scientific motivation: metastable computation as an empirically testable regime property across heterogeneous organized systems. It sets falsifiable boundaries and clarifies that claims are regularities, not universal-laws.  
content: [file reference: docs/science/manuscript/claim.md]

## 2. Formal definition of γ and observables
This section provides the operational definition of \(\gamma\), observables \((T, C)\), regression protocol, confidence interval construction, and quality gates (data sufficiency, dynamic range, fit).  
content: [file reference: manuscript/XFORM_MANUSCRIPT_DRAFT.md]
content: [file reference: docs/science/manuscript/theory_notes.md]

## 3. Closed-loop model
This section introduces witness-based control architecture: anomaly isolation, robust median aggregation, MAD coherence gate, bounded modulation, and fault tolerance assumptions.  
content: [file reference: neosynaptex.py]

## 4. Stability of the closed loop (Propositions A+B)
This section states assumptions, Lyapunov candidate \(V_\gamma(e)\), and the two formal propositions for unique attracting critical interval and binary asymptotic structure with collapse.  
content: [file reference: docs/science/manuscript/section_2_3_closed_loop.md]

## 5. Cross-substrate empirical results
This section consolidates empirical \(\gamma\) estimates and confidence intervals across substrates, preserving evidence tiers and substrate-role separation.  
Anchor tags for claim verification: zebrafish \(\gamma={evidence:zebrafish_wt:gamma}\), BN-Syn \(\gamma={evidence:bnsyn:gamma}\), NFI unified \(\gamma={evidence:nfi_unified:gamma}\).  
content: [file reference: evidence/gamma_ledger.json]
content: [file reference: docs/science/manuscript/substrate_independence.md]

## 6. Strong nulls
This section reports null-family outcomes (shuffle, block-shuffle, IAAFT) with p-values, null medians, and separation against constrained surrogates.  
content: [file reference: core/surrogates.py]

## 7. Multiverse robustness
This section summarizes 432-pipeline robustness per substrate, including distributional ranges, CI-behavior fractions, and null-robustness aggregates.  
content: [file reference: scripts/multiverse_sweep.py]

## 8. Basin structure / computational evidence
This section maps critical/collapse/unresolved basins over \((\gamma_0, sr_0, Q_0)\) with parameter sweeps, sensitivity, and unresolved fraction diagnostics.  
content: [file reference: scripts/basin_exhaustion.py]

## 9. Discussion
This section interprets empirical regularity, mechanism limits, and evidence hierarchy constraints without overclaiming beyond theorem/computation support.  
content: [file reference: docs/science/manuscript/claim.md]
content: [file reference: docs/science/manuscript/mechanistic_bridge.md]

## 10. Limitations
This section lists dependence assumptions, surrogate limitations, unresolved-basin caveats, parameter identifiability, and external-validity constraints.  
content: [file reference: docs/science/manuscript/figures.md]

## Supplement plan (S1-S7)
- S1 block bootstrap + \(N_{\mathrm{eff}}\)  
- S2 surrogate protocols  
- S3 multiverse specification  
- S4 anomaly isolation + control aggregation  
- S5 basin computation details  
- S6 reproducibility manifest  
- S7 external data provenance  
content: [file reference: scripts/generate_manifest.py]
