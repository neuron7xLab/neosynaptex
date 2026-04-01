# Zebrafish gamma-Scaling Validation Report

**Evidence type**: REAL DATA
**Timestamp**: 2026-03-28T23:51:37.546218+00:00

## Results

| Phenotype | gamma | R2 | p-value | CI95 | gamma~1.0? | Verdict |
|-----------|-------|----|---------|------|------------|---------|
| Wild-type | 11.999 | 0.250 | 0.0020 | [5.109, 13.231] | NO | INVALID |
| Mutant    | 0.038 | -0.004 | 0.9940 | [0.038, 0.038] | NO | INVALID |
| Transition | -10.472 | 0.088 | 0.0040 | [-18.550, -2.696] | NO | INVALID |

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