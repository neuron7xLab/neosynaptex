# neosynaptex — Scientific Bibliography

> **Version:** 2.0 | **Standard:** Hierarchical DOI-verified | **Verified:** 2026-03-31
> **Repository:** [github.com/neuron7xLab/neosynaptex](https://github.com/neuron7xLab/neosynaptex)
> **Role in NFI platform:** Integrating mirror layer — cross-substrate gamma-scaling diagnostics

---

## Source Hierarchy

| Tier | Definition | Criteria | Count |
|------|-----------|----------|-------|
| **F** | **Foundational** | Field-defining work cited >5 000x; establishes the theory this system implements | 8 |
| **A** | **Primary** | Peer-reviewed journal/conference paper with DOI; provides specific parameters or methods | 22 |
| **B** | **Monograph** | Authoritative reference work (Springer, CUP, MIT Press, SIAM); pedagogical authority | 8 |
| **S** | **Standard** | NeurIPS, ACM, ISO reproducibility specifications | 2 |

**Total:** 40 sources | **DOI-verified:** 34 | **ISBN-only:** 4 | **URL-only:** 2

---

## Subsystem-to-Source Traceability

| Pipeline layer | Module | Primary sources | Tier |
|---------------|--------|-----------------|------|
| **Layer 1: Collect** | `observe()` adapters | Kuramoto 1984; Acebrón+ 2005; Pikovsky+ 2001 | F, A, B |
| **Layer 2: Jacobian** | Spectral radius ρ(J) | May 1972; Sompolinsky+ 1988 | F, A |
| **Layer 3: Gamma** | K ~ C^{−γ} regression | Clauset+ 2009; Efron & Tibshirani 1993; DiCiccio & Efron 1996 | A, B |
| **Layer 4: Phase** | Phase portrait reconstruction | Takens 1981; Kantz & Schreiber 2003 | F, B |
| **Layer 5: Signal** | Granger graph, anomaly | Granger 1969; Barnett & Seth 2014; Seth+ 2015; Chandola+ 2009 | F, A |
| **Criticality theory** | Avalanche validation | Bak+ 1987; Beggs & Plenz 2003; Muñoz 2018; Mora & Bialek 2011 | F, A |
| **Metastability** | State classification | Kelso 1995; Tognoli & Kelso 2014; Shanahan 2010 | B, A |
| **Cross-domain scaling** | γ ≈ 1.0 invariant | West+ 1997; Mora & Bialek 2011; Fries 2005, 2015; Buzsáki & Wang 2012 | A, F |
| **Zebrafish substrate** | d = 47, γ_WT = 1.043 | McGuirl+ 2020; Turing 1952 | A, F |
| **R-D substrate** | Gray-Scott patterns | Turing 1952; Pearson 1993 | F, A |
| **Spiking substrate** | AdEx / BN-Syn | Brette & Gerstner 2005; Wilting & Priesemann 2018 | A |
| **Market substrate** | Econophysics scaling | Mantegna & Stanley 1999; Sornette 2003 | B |
| **AdapterHealthMonitor** | Circuit breaker | Nygard 2018 | B |
| **Bootstrap CI** | Confidence intervals | Efron & Tibshirani 1993; DiCiccio & Efron 1996 | B, A |

---

## F. Foundational

**[F1]** Turing A.M. (1952). The chemical basis of morphogenesis. *Phil. Trans. R. Soc. B*, 237(641), 37--72. DOI: [10.1098/rstb.1952.0012](https://doi.org/10.1098/rstb.1952.0012)
Reaction-diffusion morphogenesis — theoretical origin of the R-D substrate.

**[F2]** Granger C.W.J. (1969). Investigating causal relations by econometric models and cross-spectral methods. *Econometrica*, 37(3), 424--438. DOI: [10.2307/1912791](https://doi.org/10.2307/1912791)
Original Granger causality — directed information flow between substrates (Layer 5).

**[F3]** May R.M. (1972). Will a large complex system be stable? *Nature*, 238, 413--414. DOI: [10.1038/238413a0](https://doi.org/10.1038/238413a0)
Spectral radius ↔ stability — basis for the Jacobian layer diagnostic.

**[F4]** Takens F. (1981). Detecting strange attractors in turbulence. *Lect. Notes Math.*, 898, 366--381. DOI: [10.1007/BFb0091924](https://doi.org/10.1007/BFb0091924)
Embedding theorem for phase portrait reconstruction from scalar time series (Layer 4).

**[F5]** Bak P., Tang C., Wiesenfeld K. (1987). Self-organized criticality: An explanation of the 1/f noise. *Phys. Rev. Lett.*, 59(4), 381--384. DOI: [10.1103/PhysRevLett.59.381](https://doi.org/10.1103/PhysRevLett.59.381)
SOC theory — universal power-law scaling at edge of chaos.

**[F6]** Sompolinsky H., Crisanti A., Sommers H.J. (1988). Chaos in random neural networks. *Phys. Rev. Lett.*, 61(3), 259--262. DOI: [10.1103/PhysRevLett.61.259](https://doi.org/10.1103/PhysRevLett.61.259)
Edge-of-chaos transition at spectral radius = 1 — Jacobian layer reference.

**[F7]** Kuramoto Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer. DOI: [10.1007/978-3-642-69689-3](https://doi.org/10.1007/978-3-642-69689-3)
Phase-oscillator model — cross-substrate synchronization measurement.

**[F8]** Fries P. (2005). A mechanism for cognitive dynamics: Neuronal communication through neuronal coherence. *Trends Cogn. Sci.*, 9(10), 474--480. DOI: [10.1016/j.tics.2005.08.011](https://doi.org/10.1016/j.tics.2005.08.011)
Communication-through-coherence — functional rationale for gamma scaling.

---

## A. Primary Peer-Reviewed

**[A1]** Acebrón J.A., Bonilla L.L., Pérez Vicente C.J., Ritort F., Spigler R. (2005). The Kuramoto model: A simple paradigm for synchronization phenomena. *Rev. Mod. Phys.*, 77(1), 137--185. DOI: [10.1103/RevModPhys.77.137](https://doi.org/10.1103/RevModPhys.77.137)
Order parameter r(t) for coherence tracking across six substrates.

**[A2]** Strogatz S.H. (2000). From Kuramoto to Crawford: Exploring the onset of synchronization. *Physica D*, 143(1--4), 1--20. DOI: [10.1016/S0167-2789(00)00094-4](https://doi.org/10.1016/S0167-2789(00)00094-4)
Analytic synchronization onset — critical coupling detection.

**[A3]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
Gamma-band oscillation mechanisms — motivates the γ invariant.

**[A4]** Fries P. (2015). Rhythms for cognition: Communication through coherence. *Neuron*, 88(1), 220--235. DOI: [10.1016/j.neuron.2015.09.034](https://doi.org/10.1016/j.neuron.2015.09.034)
Updated CTC hypothesis — gamma scaling ↔ computational efficiency.

**[A5]** Beggs J.M., Plenz D. (2003). Neuronal avalanches in neocortical circuits. *J. Neurosci.*, 23(35), 11167--11177. DOI: [10.1523/JNEUROSCI.23-35-11167.2003](https://doi.org/10.1523/JNEUROSCI.23-35-11167.2003)
Avalanche power-law statistics — criticality validation reference.

**[A6]** Clauset A., Shalizi C.R., Newman M.E.J. (2009). Power-law distributions in empirical data. *SIAM Rev.*, 51(4), 661--703. DOI: [10.1137/070710111](https://doi.org/10.1137/070710111)
Gold-standard power-law fitting — gamma exponent validation.

**[A7]** Muñoz M.A. (2018). Colloquium: Criticality and dynamical scaling in living systems. *Rev. Mod. Phys.*, 90(3), 031001. DOI: [10.1103/RevModPhys.90.031001](https://doi.org/10.1103/RevModPhys.90.031001)
Scaling exponents ↔ biological function — framework for γ ~ 1.0.

**[A8]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
Metastability formal definition — state classification in neosynaptex.

**[A9]** Shanahan M. (2010). Metastable chimera states in community-structured oscillator networks. *Chaos*, 20(1), 013108. DOI: [10.1063/1.3305451](https://doi.org/10.1063/1.3305451)
Chimera states — partial-synchronization patterns in cross-substrate analysis.

**[A10]** Barnett L., Seth A.K. (2014). The MVGC multivariate Granger causality toolbox. *J. Neurosci. Methods*, 223, 50--68. DOI: [10.1016/j.jneumeth.2013.10.018](https://doi.org/10.1016/j.jneumeth.2013.10.018)
Multivariate GC implementation — granger_graph construction.

**[A11]** Seth A.K., Barrett A.B., Barnett L. (2015). Granger causality analysis in neuroscience and neuroimaging. *J. Neurosci.*, 35(8), 3293--3297. DOI: [10.1523/JNEUROSCI.4399-14.2015](https://doi.org/10.1523/JNEUROSCI.4399-14.2015)
Best-practices for neural GC — signal layer methodology.

**[A12]** McGuirl M.R., Volkening A., Sandstede B. (2020). Topological data analysis of zebrafish patterns. *PLoS Comput. Biol.*, 16(3), e1007679. DOI: [10.1371/journal.pcbi.1007679](https://doi.org/10.1371/journal.pcbi.1007679)
TDA on zebrafish patterning — primary reference (d = 47, γ_WT = 1.043).

**[A13]** Pearson J.E. (1993). Complex patterns in a simple system. *Science*, 261(5118), 189--192. DOI: [10.1126/science.261.5118.189](https://doi.org/10.1126/science.261.5118.189)
Gray-Scott pattern zoo — R-D substrate parameter regimes.

**[A14]** Brette R., Gerstner W. (2005). Adaptive exponential integrate-and-fire model. *J. Neurophysiol.*, 94(5), 3637--3642. DOI: [10.1152/jn.00686.2005](https://doi.org/10.1152/jn.00686.2005)
AdEx neuron model — spiking network substrate.

**[A15]** Wilting J., Priesemann V. (2018). Inferring collective dynamical states from widely unobserved systems. *Nat. Commun.*, 9, 2325. DOI: [10.1038/s41467-018-04725-4](https://doi.org/10.1038/s41467-018-04725-4)
MR estimator — subsampling-corrected branching ratio.

**[A16]** DiCiccio T.J., Efron B. (1996). Bootstrap confidence intervals. *Stat. Sci.*, 11(3), 189--228. DOI: [10.1214/ss/1032280214](https://doi.org/10.1214/ss/1032280214)
BCa bootstrap with bias correction — CI construction on γ estimates.

**[A17]** Chandola V., Banerjee A., Kumar V. (2009). Anomaly detection: A survey. *ACM Comput. Surv.*, 41(3), 1--58. DOI: [10.1145/1541880.1541882](https://doi.org/10.1145/1541880.1541882)
Anomaly detection methods — anomaly_score computation.

**[A18]** West G.B., Brown J.H., Enquist B.J. (1997). A general model for the origin of allometric scaling laws in biology. *Science*, 276(5309), 122--126. DOI: [10.1126/science.276.5309.122](https://doi.org/10.1126/science.276.5309.122)
Universal allometric scaling from fractal geometry — γ ~ 1.0 invariant theory.

**[A19]** Mora T., Bialek W. (2011). Are biological systems poised at criticality? *J. Stat. Phys.*, 144(2), 268--302. DOI: [10.1007/s10955-011-0229-4](https://doi.org/10.1007/s10955-011-0229-4)
Biological systems at critical points — universal γ hypothesis support.

**[A20]** Schreiber T. (2000). Measuring information transfer. *Phys. Rev. Lett.*, 85(2), 461--464. DOI: [10.1103/PhysRevLett.85.461](https://doi.org/10.1103/PhysRevLett.85.461)
Transfer entropy — non-linear directed information flow complement to Granger.

**[A21]** Strogatz S.H. (2001). Exploring complex networks. *Nature*, 410, 268--276. DOI: [10.1038/35065725](https://doi.org/10.1038/35065725)
Complex network topology survey — cross-substrate coupling structure.

**[A22]** Wolf A., Swift J.B., Swinney H.L., Vastano J.A. (1985). Determining Lyapunov exponents from a time series. *Physica D*, 16(3), 285--317. DOI: [10.1016/0167-2789(85)90011-9](https://doi.org/10.1016/0167-2789(85)90011-9)
Lyapunov exponent computation — dynamical stability characterization in phase portraits.

---

## B. Monographs and Textbooks

**[B1]** Pikovsky A., Rosenblum M., Kurths J. (2001). *Synchronization: A Universal Concept in Nonlinear Sciences*. CUP. DOI: [10.1017/CBO9780511755743](https://doi.org/10.1017/CBO9780511755743)
Synchronization across physical/chemical/biological systems.

**[B2]** Kelso J.A.S. (1995). *Dynamic Patterns: The Self-Organization of Brain and Behavior*. MIT Press. ISBN: 978-0262611312.
Coordination dynamics and metastability — conceptual foundation.

**[B3]** Efron B., Tibshirani R.J. (1993). *An Introduction to the Bootstrap*. CRC. DOI: [10.1007/978-1-4899-4541-9](https://doi.org/10.1007/978-1-4899-4541-9)
Bootstrap CI methodology — all γ CI computations.

**[B4]** Mantegna R.N., Stanley H.E. (1999). *Introduction to Econophysics*. CUP. DOI: [10.1017/CBO9780511755767](https://doi.org/10.1017/CBO9780511755767)
Econophysics scaling — market substrate.

**[B5]** Sornette D. (2003). *Why Stock Markets Crash*. Princeton. ISBN: 978-0691118505.
Critical phenomena in markets — market regime detection.

**[B6]** Kantz H., Schreiber T. (2003). *Nonlinear Time Series Analysis*. CUP, 2nd ed. DOI: [10.1017/CBO9780511755798](https://doi.org/10.1017/CBO9780511755798)
Embedding, Lyapunov, correlation dimensions — phase-space analysis.

**[B7]** Nygard M. (2018). *Release It!* Pragmatic Bookshelf, 2nd ed. ISBN: 978-1680502398.
Circuit-breaker pattern (CLOSED → OPEN → HALF_OPEN) — AdapterHealthMonitor.

**[B8]** Strogatz S.H. (2015). *Nonlinear Dynamics and Chaos*. Westview, 2nd ed. ISBN: 978-0813349107.
Standard dynamical systems reference — bifurcation, attractors, stability.

---

## S. Standards and Specifications

**[S1]** NeurIPS Paper Checklist (2024). https://neurips.cc/public/guides/PaperChecklist
Reproducibility checklist — evidence bundles.

**[S2]** ACM Artifact Review and Badging v1.1 (2020). https://www.acm.org/publications/policies/artifact-review-and-badging-current
Artifact evaluation criteria — proof bundle.

---

## Cross-Platform Reference Network

Sources shared with other neuron7xLab repositories:

| Source | neosynaptex | bnsyn | MFN | agents | CA1 | mlsdm |
|--------|:-----------:|:-----:|:---:|:------:|:---:|:-----:|
| Kuramoto 1984 | **x** | | **x** | **x** | | |
| Acebrón+ 2005 | **x** | | **x** | **x** | | |
| Beggs & Plenz 2003 | **x** | **x** | | **x** | | |
| Buzsáki & Wang 2012 | **x** | **x** | | **x** | | |
| Tognoli & Kelso 2014 | **x** | **x** | | **x** | | |
| McGuirl+ 2020 | **x** | **x** | **x** | **x** | | |
| Turing 1952 | **x** | | **x** | | | |
| Granger 1969 | **x** | | **x** | | | |
| Mora & Bialek 2011 | **x** | | **x** | | | |
| Clauset+ 2009 | **x** | **x** | | | | |
| Brette & Gerstner 2005 | **x** | **x** | | | | |
| Wilting & Priesemann 2018 | **x** | **x** | | | | |

---

## Verification Protocol

All DOIs verified via CrossRef API or doi.org resolution on 2026-03-31.
ISBN entries verified via WorldCat or publisher catalogue.
To verify: `curl -sL "https://doi.org/[DOI]" -o /dev/null -w "%{http_code}"` → expect `302` or `200`.

**Policy:** Normative scientific claims cite Tier-F or Tier-A sources only. Architectural/process claims may cite Tier-B or Tier-S.

---

## Citation

```bibtex
@software{vasylenko2026_neosynaptex,
  author  = {Vasylenko, Yaroslav},
  title   = {neosynaptex: NFI Integrating Mirror Layer},
  year    = {2026},
  url     = {https://github.com/neuron7xLab/neosynaptex},
  version = {1.0.0}
}
```
