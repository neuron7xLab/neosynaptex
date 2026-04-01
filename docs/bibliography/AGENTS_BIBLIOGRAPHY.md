# neuron7x-agents — Scientific Bibliography

> **Version:** 2.0 | **Standard:** Hierarchical DOI-verified | **Verified:** 2026-03-31
> **Repository:** [github.com/neuron7xLab/neuron7x-agents](https://github.com/neuron7xLab/neuron7x-agents)
> **Role in NFI platform:** Hybrid cognitive functions — DNCA, NCE, SERO, Kriterion

---

## Source Hierarchy

| Tier | Definition | Criteria | Count |
|------|-----------|----------|-------|
| **F** | **Foundational** | Field-defining work cited >5 000x; establishes the theory this system implements | 7 |
| **A** | **Primary** | Peer-reviewed journal/conference paper with DOI; provides specific parameters or methods | 24 |
| **B** | **Monograph** | Authoritative reference work; pedagogical authority | 4 |
| **S** | **Standard** | NeurIPS, ACM reproducibility specifications | 0 |

**Total:** 35 sources | **DOI-verified:** 30 | **ISBN/PMID-only:** 4 | **URL-only:** 1

---

## Subsystem-to-Source Traceability

| Subsystem | Module path | Primary sources | Tier |
|-----------|------------|-----------------|------|
| **DNCA core** | `dnca/` | Doya 2002; Rabinovich+ 2008 | F, A |
| **DA operator** | `dnca/operators/` | Schultz+ 1997 | F |
| **NE operator** | `dnca/operators/` | Aston-Jones & Cohen 2005 | A |
| **ACh operator** | `dnca/operators/` | Hasselmo 2006 | A |
| **5-HT operator** | `dnca/operators/` | Cools+ 2011 | A |
| **GABA operator** | `dnca/operators/` | Mann & Paulsen 2007 | A |
| **Glu operator** | `dnca/operators/` | Meldrum 2000 | A |
| **Lotka-Volterra** | `dnca/dynamics/` | Lotka 1925; May 1976; Rabinovich+ 2008 | B, A |
| **Kuramoto coupling** | `dnca/coupling/` | Kuramoto 1984; Acebrón+ 2005 | F, A |
| **Gamma probe (TDA)** | `dnca/gamma_probe/` | Edelsbrunner+ 2002; Carlsson 2009; McGuirl+ 2020 | F, A |
| **NCE predictive coding** | `cognitive/engine/` | Rao & Ballard 1999; Friston 2010; Clark 2013 | F, A |
| **NCE abductive inference** | `cognitive/engine/` | Harman 1965; Lipton 2004 | A, B |
| **NCE epistemic foraging** | `cognitive/engine/` | Friston+ 2015 | A |
| **SERO stress regulation** | `regulation/hvr/` | Ashby 1956; Åström & Murray 2008 | B |
| **SERO immune system** | `regulation/immune/` | Matzinger 2002; Jerne 1974 | A |
| **Kriterion evidence gate** | `verification/` | Pearl 1988; Friston 2013 | F, A |
| **Cortical Column** | `primitives/` | Mountcastle 1997; Bastos+ 2012 | A |
| **Metastability health** | `dnca/health/` | Tognoli & Kelso 2014; Beggs & Plenz 2003 | A |

---

## F. Foundational

**[F1]** Kuramoto Y. (1984). *Chemical Oscillations, Waves, and Turbulence*. Springer. DOI: [10.1007/978-3-642-69689-3](https://doi.org/10.1007/978-3-642-69689-3)
Phase-oscillator coupling — DNCA inter-operator synchronization.

**[F2]** Rao R.P.N., Ballard D.H. (1999). Predictive coding in the visual cortex. *Nat. Neurosci.*, 2(1), 79--87. DOI: [10.1038/4580](https://doi.org/10.1038/4580)
Predict → observe → error → update — NCE core mechanism.

**[F3]** Doya K. (2002). Metalearning and neuromodulation. *Neural Networks*, 15(4--6), 495--506. DOI: [10.1016/S0893-6080(02)00044-8](https://doi.org/10.1016/S0893-6080(02)00044-8)
DA/5-HT/NE/ACh ↔ reward/discount/uncertainty/attention — DNCA six-operator architecture.

**[F4]** Schultz W., Dayan P., Montague P.R. (1997). A neural substrate of prediction and reward. *Science*, 275(5306), 1593--1599. DOI: [10.1126/science.275.5306.1593](https://doi.org/10.1126/science.275.5306.1593)
Dopamine = reward prediction error — DA operator.

**[F5]** Friston K. (2010). The free-energy principle: A unified brain theory? *Nat. Rev. Neurosci.*, 11(2), 127--138. DOI: [10.1038/nrn2787](https://doi.org/10.1038/nrn2787)
FEP unifying perception/action/learning — NCE theoretical foundation.

**[F6]** Pearl J. (1988). *Probabilistic Reasoning in Intelligent Systems*. Morgan Kaufmann. DOI: [10.1016/C2009-0-27609-4](https://doi.org/10.1016/C2009-0-27609-4)
Markov blankets in Bayesian networks — Kriterion evidence boundary.

**[F7]** Edelsbrunner H., Letscher D., Zomorodian A. (2002). Topological persistence and simplification. *Discrete Comput. Geom.*, 28(4), 511--533. DOI: [10.1007/s00454-002-2885-2](https://doi.org/10.1007/s00454-002-2885-2)
Persistent homology — TDA-based gamma probe.

---

## A. Primary Peer-Reviewed

**[A1]** Aston-Jones G., Cohen J.D. (2005). An integrative theory of locus coeruleus-norepinephrine function. *Annu. Rev. Neurosci.*, 28, 403--450. DOI: [10.1146/annurev.neuro.28.061604.135709](https://doi.org/10.1146/annurev.neuro.28.061604.135709)
Adaptive-gain theory — NE operator tonic/phasic modes.

**[A2]** Hasselmo M.E. (2006). The role of acetylcholine in learning and memory. *Curr. Opin. Neurobiol.*, 16(6), 710--715. DOI: [10.1016/j.conb.2006.09.002](https://doi.org/10.1016/j.conb.2006.09.002)
ACh modulates encoding vs retrieval — ACh operator.

**[A3]** Cools R., Nakamura K., Daw N.D. (2011). Serotonin and dopamine: Unifying affective, activational, and decision functions. *Neuropsychopharmacology*, 36(1), 98--113. DOI: [10.1038/npp.2010.121](https://doi.org/10.1038/npp.2010.121)
5-HT = patience/harm aversion — 5-HT operator.

**[A4]** Mann E.O., Paulsen O. (2007). Role of GABAergic inhibition in hippocampal network oscillations. *Trends Neurosci.*, 30(7), 343--349. DOI: [10.1016/j.tins.2007.05.003](https://doi.org/10.1016/j.tins.2007.05.003)
GABA gates oscillatory dynamics — GABA operator.

**[A5]** Meldrum B.S. (2000). Glutamate as a neurotransmitter in the brain. *J. Nutr.*, 130(4S), 1007S--1015S. DOI: [10.1093/jn/130.4.1007S](https://doi.org/10.1093/jn/130.4.1007S)
Glutamate excitatory physiology — Glu operator.

**[A6]** May R.M. (1976). Simple mathematical models with very complicated dynamics. *Nature*, 261, 459--467. DOI: [10.1038/261459a0](https://doi.org/10.1038/261459a0)
Bifurcation and chaos in ecological models — DNCA stability analysis.

**[A7]** Rabinovich M.I., Huerta R., Varona P., Afraimovich V.S. (2008). Transient cognitive dynamics, metastability, and decision making. *PLoS Comput. Biol.*, 4(5), e1000072. DOI: [10.1371/journal.pcbi.1000072](https://doi.org/10.1371/journal.pcbi.1000072)
Winnerless competition (generalized LV) — DNCA dominant-regime succession.

**[A8]** Acebrón J.A., Bonilla L.L., Pérez Vicente C.J., Ritort F., Spigler R. (2005). The Kuramoto model: A simple paradigm for synchronization phenomena. *Rev. Mod. Phys.*, 77(1), 137--185. DOI: [10.1103/RevModPhys.77.137](https://doi.org/10.1103/RevModPhys.77.137)
Kuramoto review — order parameter r(t) in DNCA coherence.

**[A9]** Friston K., Kilner J., Harrison L. (2006). A free energy principle for the brain. *J. Physiol. Paris*, 100(1--3), 70--87. DOI: [10.1016/j.jphysparis.2006.10.001](https://doi.org/10.1016/j.jphysparis.2006.10.001)
FEP mathematical formulation — NCE update equations.

**[A10]** Clark A. (2013). Whatever next? Predictive brains, situated agents, and the future of cognitive science. *Behav. Brain Sci.*, 36(3), 181--204. DOI: [10.1017/S0140525X12000477](https://doi.org/10.1017/S0140525X12000477)
Predictive processing framework — NCE design rationale.

**[A11]** Friston K., Rigoli F., Ognibene D., Mathys C., Fitzgerald T., Pezzulo G. (2015). Active inference and epistemic value. *Cogn. Neurosci.*, 6(4), 187--214. DOI: [10.1080/17588928.2015.1020053](https://doi.org/10.1080/17588928.2015.1020053)
Epistemic foraging via active inference — NCE primitive.

**[A12]** Harman G. (1965). The inference to the best explanation. *Philos. Rev.*, 74(1), 88--95. DOI: [10.2307/2183532](https://doi.org/10.2307/2183532)
IBE — abductive inference ranking in NCE.

**[A13]** Carlsson G. (2009). Topology and data. *Bull. Amer. Math. Soc.*, 46(2), 255--308. DOI: [10.1090/S0273-0979-09-01249-X](https://doi.org/10.1090/S0273-0979-09-01249-X)
TDA survey — gamma probe methodology.

**[A14]** Friston K. (2013). Life as we know it. *J. R. Soc. Interface*, 10(86), 20130475. DOI: [10.1098/rsif.2013.0475](https://doi.org/10.1098/rsif.2013.0475)
Markov blankets as self-organizing boundaries — DNCA agent boundary.

**[A15]** Matzinger P. (2002). The danger model: A renewed sense of self. *Science*, 296(5566), 301--305. DOI: [10.1126/science.1071059](https://doi.org/10.1126/science.1071059)
Danger model (dual-signal threat detection) — SERO immune system.

**[A16]** Jerne N.K. (1974). Towards a network theory of the immune system. *Ann. Immunol. (Inst. Pasteur)*, 125C(1--2), 373--389. PMID: 4142565.
Idiotypic network theory — dual-channel alert architecture.

**[A17]** Cardin J.A. et al. (2009). Driving fast-spiking cells induces gamma rhythm and controls sensory responses. *Nature*, 459(7247), 663--667. DOI: [10.1038/nature08002](https://doi.org/10.1038/nature08002)
PV+ interneurons generate gamma via PING — cited in examples.

**[A18]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
Gamma power ↔ cognitive load — reference for examples.

**[A19]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
Metastability — DNCA dominant-regime transitions.

**[A20]** Beggs J.M., Plenz D. (2003). Neuronal avalanches in neocortical circuits. *J. Neurosci.*, 23(35), 11167--11177. DOI: [10.1523/JNEUROSCI.23-35-11167.2003](https://doi.org/10.1523/JNEUROSCI.23-35-11167.2003)
Criticality validation — gamma probe.

**[A21]** McGuirl M.R., Volkening A., Sandstede B. (2020). TDA of zebrafish patterns. *PLoS Comput. Biol.*, 16(3), e1007679. DOI: [10.1371/journal.pcbi.1007679](https://doi.org/10.1371/journal.pcbi.1007679)
γ_WT = +1.043 — external validation for γ_DNCA ~ 1.0.

**[A22]** Mountcastle V.B. (1997). The columnar organization of the neocortex. *Brain*, 120(4), 701--722. DOI: [10.1093/brain/120.4.701](https://doi.org/10.1093/brain/120.4.701)
Cortical minicolumn — Cortical Column primitive.

**[A23]** Bastos A.M., Usrey W.M., Adams R.A., Mangun G.R., Fries P., Friston K.J. (2012). Canonical microcircuits for predictive coding. *Neuron*, 76(4), 695--711. DOI: [10.1016/j.neuron.2012.10.038](https://doi.org/10.1016/j.neuron.2012.10.038)
Predictive coding microcircuits — Creator → Critic → Auditor → Verifier.

**[A24]** Parr T., Pezzulo G., Friston K.J. (2022). *Active Inference: The Free Energy Principle in Mind, Brain, and Behavior*. MIT Press. DOI: [10.7551/mitpress/12441.001.0001](https://doi.org/10.7551/mitpress/12441.001.0001)
Comprehensive active inference textbook — NCE theoretical integration.

---

## B. Monographs and Textbooks

**[B1]** Lotka A.J. (1925). *Elements of Physical Biology*. Williams & Wilkins. Reprinted: Dover, 1956.
Competitive dynamics — Lotka-Volterra competition framework.

**[B2]** Ashby W.R. (1956). *An Introduction to Cybernetics*. Chapman & Hall. Available: http://pespmc1.vub.ac.be/books/IntroCyb.pdf
Requisite variety, homeostatic regulation — SERO throughput guarantee.

**[B3]** Lipton P. (2004). *Inference to the Best Explanation*. Routledge, 2nd ed. ISBN: 978-0415242028.
Abductive reasoning — NCE hypothesis evaluation.

**[B4]** Åström K.J., Murray R.M. (2008). *Feedback Systems*. Princeton. ISBN: 978-0691135762.
Control theory — SERO damping and stability.

---

## Cross-Platform Reference Network

| Source | agents | neosynaptex | bnsyn | MFN | CA1 | mlsdm |
|--------|:------:|:-----------:|:-----:|:---:|:---:|:-----:|
| Kuramoto 1984 | **x** | **x** | | **x** | | |
| Acebrón+ 2005 | **x** | **x** | | **x** | | |
| Doya 2002 | **x** | | | **x** | | |
| Schultz+ 1997 | **x** | | | **x** | | |
| Friston 2010 | **x** | | | | | |
| Edelsbrunner+ 2002 | **x** | | | **x** | | |
| Beggs & Plenz 2003 | **x** | **x** | **x** | | | |
| Buzsáki & Wang 2012 | **x** | **x** | **x** | | | |
| Tognoli & Kelso 2014 | **x** | **x** | **x** | | | |
| McGuirl+ 2020 | **x** | **x** | **x** | **x** | | |
| Turrigiano 2012 | | | **x** | **x** | | **x** |

---

## Verification Protocol

All DOIs verified via CrossRef API or doi.org resolution on 2026-03-31.
PMID entries verified via PubMed. ISBN entries verified via WorldCat.
To verify: `curl -sL "https://doi.org/[DOI]" -o /dev/null -w "%{http_code}"` → expect `302` or `200`.

**Policy:** Normative scientific claims cite Tier-F or Tier-A sources only.

---

## Citation

```bibtex
@software{vasylenko2026_agents,
  author  = {Vasylenko, Yaroslav},
  title   = {neuron7x-agents: Hybrid Cognitive Functions for Intelligent Systems},
  year    = {2026},
  url     = {https://github.com/neuron7xLab/neuron7x-agents},
  version = {1.0.0}
}
```
