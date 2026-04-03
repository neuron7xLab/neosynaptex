# Evidence Index

Maps manuscript claims to evidence artifacts and validating tests.

## Core Universality Claim

**Claim:** γ ≈ 1.0 across 4 independent physical substrates (mean γ = 0.985 ± 0.097).

| Substrate | γ | Evidence Source | Validating Test | Status |
|-----------|---|----------------|-----------------|--------|
| Zebrafish morphogenesis | 1.043 | `gamma_ledger.json:zebrafish_wt` | `test_zebrafish_real.py` | VALIDATED |
| Gray-Scott reaction-diffusion | 0.979 | `gamma_ledger.json:gray_scott` | `test_gray_scott_real.py` | VALIDATED |
| BN-Syn spiking criticality | 0.946 | `gamma_ledger.json:bnsyn` | `test_bnsyn_real.py` | VALIDATED |
| Kuramoto market coherence | 0.963 | `gamma_ledger.json:kuramoto` | `test_kuramoto_real.py` | VALIDATED |

## Cross-Substrate Invariant

| Claim | Evidence | Test | Status |
|-------|----------|------|--------|
| All 4 independent CI contain γ=1.0 | `xform_proof_bundle.json:substrates` | `test_gamma_invariant.py` | VALIDATED |
| Mean γ near unity | `xform_proof_bundle.json:universal_gamma` | `test_gamma_invariant.py` | VALIDATED |

## Illustrative Substrates (non-evidential)

| Substrate | γ | Reason for Exclusion | Evidence |
|-----------|---|---------------------|----------|
| Neosynaptex cross-domain | 1.030 | Pseudo-replication (aggregate of other substrates) | `xform_proof_bundle.json:illustrative_substrates` |
| CNS-AI productive | 1.138 | Self-measurement bias, R²=0.12 | `xform_proof_bundle.json:illustrative_substrates` |
| CNS-AI non-productive | -0.557 | Self-measurement bias, R²=-0.10 | `xform_proof_bundle.json:illustrative_substrates` |

## Surrogate Tests (Hole 7)

| Claim | Evidence | Test | Status |
|-------|----------|------|--------|
| γ not artifact of sample structure | `surrogate_evidence.json` | `test_negative_controls.py` | PENDING |
| IAAFT null preserves spectrum | `surrogate_evidence.json:surrogate_tests` | `test_iaaft.py` | VALIDATED |

## Negative Controls (Hole 6)

| Control | Expected γ | Evidence | Test |
|---------|-----------|----------|------|
| White noise | ≠ 1.0 | `surrogate_evidence.json:negative_controls` | `test_negative_controls.py` |
| Random walk | ≠ 1.0 | `surrogate_evidence.json:negative_controls` | `test_negative_controls.py` |
| Supercritical | << 1.0 | `surrogate_evidence.json:negative_controls` | `test_negative_controls.py` |
| Subcritical ordered | >> 1.0 | `surrogate_evidence.json:negative_controls` | `test_negative_controls.py` |

## Evidence Artifacts Inventory

| File | Content | Frozen At |
|------|---------|-----------|
| `gamma_ledger.json` | Master γ registry (11 entries) | 2026-04-02 |
| `registry.json` | Global evidence registry | — |
| `failure_regimes.json` | Circuit breaker failure modes | — |
| `surrogate_evidence.json` | IAAFT surrogates + negative controls | 2026-04-03 |
| `EVIDENCE_INDEX.md` | This file | — |
