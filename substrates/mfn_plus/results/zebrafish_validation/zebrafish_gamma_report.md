# Zebrafish gamma-Scaling Validation Report

**Evidence type**: SYNTHETIC PROXY
**Timestamp**: 2026-03-28T23:41:54.088271+00:00

## Results

| Phenotype | gamma | R2 | p-value | CI95 | gamma~1.0? | Verdict |
|-----------|-------|----|---------|------|------------|---------|
| Wild-type | -20.229 | 0.019 | 0.6080 | [-129.169, 33.441] | NO | INVALID |
| Mutant    | 2.651 | 0.009 | 0.0600 | [-0.652, 4.832] | NO | INVALID |
| Transition | 3.071 | 0.190 | 0.0020 | [1.389, 4.369] | NO | INVALID |

## Organoid Reference

gamma_organoid (Vasylenko 2026, Zenodo 10301912) = **1.487 +/- 0.208**
Wild-type gamma in organoid CI [1.279, 1.695]: **False**

## Falsification Verdict

**INCONCLUSIVE**

> Hypothesis (Vasylenko-Levin-Tononi): Wild-type gamma ~ +1.0, Mutant gamma != 1.0.

## Notes


## References

- McGuirl et al. (2020) PNAS 117(10):5217-5224. DOI: 10.1073/pnas.1917038117
- Vasylenko (2026) gamma-scaling on brain organoids. Zenodo 10301912
- Theil (1950), Sen (1968): robust slope estimator