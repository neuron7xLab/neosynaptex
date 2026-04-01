# BN-Syn — Scientific Bibliography

> **Version:** 2.0 | **Standard:** Hierarchical DOI-verified | **Verified:** 2026-03-31
> **Repository:** [github.com/neuron7xLab/bnsyn-phase-controlled-emergent-dynamics](https://github.com/neuron7xLab/bnsyn-phase-controlled-emergent-dynamics)
> **Role in NFI platform:** Deterministic spiking neural network simulator — AdEx/STDP/criticality

---

## Source Hierarchy

| Tier | Definition | Criteria | Count |
|------|-----------|----------|-------|
| **F** | **Foundational** | Field-defining work cited >5 000x; establishes the theory this system implements | 5 |
| **A** | **Primary** | Peer-reviewed journal/conference paper with DOI; provides specific parameters or methods | 21 |
| **B** | **Monograph** | Authoritative reference work; pedagogical authority | 3 |
| **S** | **Standard** | NeurIPS, ACM, PyTorch reproducibility specifications | 3 |

**Total:** 32 sources | **DOI-verified:** 28 | **ISBN-only:** 1 | **URL-only:** 3

---

## Subsystem-to-Source Traceability

| Subsystem | Module | Primary sources | Tier |
|-----------|--------|-----------------|------|
| **AdEx neuron** | `neuron/adex.py` | Brette & Gerstner 2005; Izhikevich 2003 | F, A |
| **NMDA synapse** | `synapse/nmda.py` | Jahr & Stevens 1990 | A |
| **Three-factor STDP** | `plasticity/stdp.py` | Frémaux & Gerstner 2016; Bi & Poo 1998; Song+ 2000 | A, F |
| **DA-modulated STDP** | `plasticity/da_stdp.py` | Izhikevich 2007 | A |
| **Synaptic tagging** | `plasticity/stc.py` | Frey & Morris 1997 | A |
| **Avalanche analysis** | `analysis/avalanche.py` | Beggs & Plenz 2003; Clauset+ 2009 | F, A |
| **MR estimator** | `analysis/branching.py` | Wilting & Priesemann 2018 | A |
| **Criticality control** | `control/` | Bak+ 1987; Muñoz 2018; Shew & Plenz 2013 | F, A |
| **Sleep-wake cycle** | `rhythm/` | Tononi & Cirelli 2014; Benna & Fusi 2016 | A |
| **Metastable dynamics** | `dynamics/` | Tognoli & Kelso 2014; Rabinovich+ 2008 | A |
| **Gamma oscillations** | `oscillations/` | Buzsáki & Wang 2012 | A |
| **Homeostatic scaling** | `homeostasis/` | Turrigiano 2012 | A |
| **Cooperation model** | `cooperation/` | Trivers 1971; Axelrod & Hamilton 1981; Nowak & Sigmund 1998; Fehr & Gächter 2002 | A |
| **Annealing schedule** | `control/temperature.py` | Kirkpatrick+ 1983 | A |
| **RNG determinism** | `core/seed.py` | Matsumoto & Nishimura 1998 | A |
| **ODE integration** | `solver/` | Hairer+ 1993 | B |
| **Gamma scaling** | `gamma/` | McGuirl+ 2020 | A |
| **Reproducibility** | `proof_bundle/` | Wilkinson+ 2016 (FAIR) | A |

---

## F. Foundational

**[F1]** Brette R., Gerstner W. (2005). Adaptive exponential integrate-and-fire model. *J. Neurophysiol.*, 94(5), 3637--3642. DOI: [10.1152/jn.00686.2005](https://doi.org/10.1152/jn.00686.2005)
Canonical AdEx neuron model — core simulation.

**[F2]** Beggs J.M., Plenz D. (2003). Neuronal avalanches in neocortical circuits. *J. Neurosci.*, 23(35), 11167--11177. DOI: [10.1523/JNEUROSCI.23-35-11167.2003](https://doi.org/10.1523/JNEUROSCI.23-35-11167.2003)
Neuronal avalanches — avalanche exponents and branching ratio.

**[F3]** Bak P., Tang C., Wiesenfeld K. (1987). Self-organized criticality. *Phys. Rev. Lett.*, 59(4), 381--384. DOI: [10.1103/PhysRevLett.59.381](https://doi.org/10.1103/PhysRevLett.59.381)
SOC theory — criticality control mechanisms.

**[F4]** Bi G.-q., Poo M.-m. (1998). Synaptic modifications in cultured hippocampal neurons. *J. Neurosci.*, 18(24), 10464--10472. DOI: [10.1523/JNEUROSCI.18-24-10464.1998](https://doi.org/10.1523/JNEUROSCI.18-24-10464.1998)
STDP timing windows — canonical STDP reference.

**[F5]** Hopfield J.J. (1982). Neural networks and physical systems with emergent collective computational abilities. *PNAS*, 79(8), 2554--2558. DOI: [10.1073/pnas.79.8.2554](https://doi.org/10.1073/pnas.79.8.2554)
Energy formulations for neural systems — attractor dynamics.

---

## A. Primary Peer-Reviewed

**[A1]** Jahr C.E., Stevens C.F. (1990). Voltage dependence of NMDA-activated macroscopic conductances. *J. Neurosci.*, 10(9), 3178--3182. DOI: [10.1523/JNEUROSCI.10-09-03178.1990](https://doi.org/10.1523/JNEUROSCI.10-09-03178.1990)
NMDA Mg²⁺ block coefficients.

**[A2]** Frémaux N., Gerstner W. (2016). Neuromodulated spike-timing-dependent plasticity, and theory of three-factor learning rules. *Front. Neural Circuits*, 9, 85. DOI: [10.3389/fncir.2015.00085](https://doi.org/10.3389/fncir.2015.00085)
Three-factor learning rule.

**[A3]** Izhikevich E.M. (2007). Solving the distal reward problem through linkage of STDP and dopamine signaling. *Cereb. Cortex*, 17(10), 2443--2452. DOI: [10.1093/cercor/bhl152](https://doi.org/10.1093/cercor/bhl152)
DA-modulated STDP with eligibility traces.

**[A4]** Wilting J., Priesemann V. (2018). Inferring collective dynamical states from widely unobserved systems. *Nat. Commun.*, 9, 2325. DOI: [10.1038/s41467-018-04725-4](https://doi.org/10.1038/s41467-018-04725-4)
MR estimator for subsampling-corrected σ.

**[A5]** Clauset A., Shalizi C.R., Newman M.E.J. (2009). Power-law distributions in empirical data. *SIAM Rev.*, 51(4), 661--703. DOI: [10.1137/070710111](https://doi.org/10.1137/070710111)
Power-law validation methodology.

**[A6]** Frey U., Morris R.G.M. (1997). Synaptic tagging and long-term potentiation. *Nature*, 385, 533--536. DOI: [10.1038/385533a0](https://doi.org/10.1038/385533a0)
Synaptic tagging and capture (STC).

**[A7]** Wilkinson M.D. et al. (2016). The FAIR Guiding Principles. *Sci. Data*, 3, 160018. DOI: [10.1038/sdata.2016.18](https://doi.org/10.1038/sdata.2016.18)
FAIR principles — reproducibility.

**[A8]** Trivers R.L. (1971). The evolution of reciprocal altruism. *Q. Rev. Biol.*, 46(1), 35--57. DOI: [10.1086/406755](https://doi.org/10.1086/406755)
Reciprocal altruism — cooperation model.

**[A9]** Axelrod R., Hamilton W.D. (1981). The evolution of cooperation. *Science*, 211(4489), 1390--1396. DOI: [10.1126/science.7466396](https://doi.org/10.1126/science.7466396)
Tit-for-tat cooperation mechanism.

**[A10]** Kirkpatrick S., Gelatt C.D., Vecchi M.P. (1983). Optimization by simulated annealing. *Science*, 220(4598), 671--680. DOI: [10.1126/science.220.4598.671](https://doi.org/10.1126/science.220.4598.671)
Temperature schedule for exploration → convergence.

**[A11]** Nowak M.A., Sigmund K. (1998). Evolution of indirect reciprocity by image scoring. *Nature*, 393, 573--577. DOI: [10.1038/31225](https://doi.org/10.1038/31225)
Reputation-based cooperation (indirect reciprocity).

**[A12]** Fehr E., Gächter S. (2002). Altruistic punishment in humans. *Nature*, 415, 137--140. DOI: [10.1038/415137a](https://doi.org/10.1038/415137a)
Costly sanctioning stabilizes cooperation.

**[A13]** Tononi G., Cirelli C. (2014). Sleep and the price of plasticity. *Neuron*, 81(1), 12--34. DOI: [10.1016/j.neuron.2013.12.025](https://doi.org/10.1016/j.neuron.2013.12.025)
Synaptic homeostasis hypothesis — sleep-wake consolidation.

**[A14]** Tognoli E., Kelso J.A.S. (2014). The metastable brain. *Neuron*, 81(1), 35--48. DOI: [10.1016/j.neuron.2013.12.022](https://doi.org/10.1016/j.neuron.2013.12.022)
Metastability — phase-controlled emergent dynamics.

**[A15]** Muñoz M.A. (2018). Criticality and dynamical scaling in living systems. *Rev. Mod. Phys.*, 90(3), 031001. DOI: [10.1103/RevModPhys.90.031001](https://doi.org/10.1103/RevModPhys.90.031001)
Critical exponents ↔ biological function.

**[A16]** Shew W.L., Plenz D. (2013). The functional benefits of criticality in the cortex. *The Neuroscientist*, 19(1), 88--100. DOI: [10.1177/1073858412445487](https://doi.org/10.1177/1073858412445487)
Criticality maximizes dynamic range.

**[A17]** Song S., Miller K.D., Abbott L.F. (2000). Competitive Hebbian learning through STDP. *Nat. Neurosci.*, 3(9), 919--926. DOI: [10.1038/78829](https://doi.org/10.1038/78829)
STDP → stable weight distributions.

**[A18]** Rabinovich M.I., Huerta R., Varona P., Afraimovich V.S. (2008). Transient cognitive dynamics. *PLoS Comput. Biol.*, 4(5), e1000072. DOI: [10.1371/journal.pcbi.1000072](https://doi.org/10.1371/journal.pcbi.1000072)
Winnerless competition — metastable sequential dynamics.

**[A19]** Turrigiano G. (2012). Homeostatic synaptic plasticity. *Cold Spring Harb. Perspect. Biol.*, 4(1), a005736. DOI: [10.1101/cshperspect.a005736](https://doi.org/10.1101/cshperspect.a005736)
Homeostatic scaling — thermostated regulation.

**[A20]** Buzsáki G., Wang X.-J. (2012). Mechanisms of gamma oscillations. *Annu. Rev. Neurosci.*, 35, 203--225. DOI: [10.1146/annurev-neuro-062111-150444](https://doi.org/10.1146/annurev-neuro-062111-150444)
Gamma oscillation dynamics in spiking networks.

**[A21]** Benna M.K., Fusi S. (2016). Computational principles of synaptic memory consolidation. *Nat. Neurosci.*, 19(12), 1697--1706. DOI: [10.1038/nn.4401](https://doi.org/10.1038/nn.4401)
Multi-timescale consolidation — sleep-wake memory model.

**[A-extra]** Izhikevich E.M. (2003). Simple model of spiking neurons. *IEEE Trans. Neural Networks*, 14(6), 1569--1572. DOI: [10.1109/TNN.2003.820440](https://doi.org/10.1109/TNN.2003.820440)
Efficient spiking neuron simulation — alternative model reference.

**[A-extra]** Matsumoto M., Nishimura T. (1998). Mersenne Twister. *ACM Trans. Model. Comput. Simul.*, 8(1), 3--30. DOI: [10.1145/272991.272995](https://doi.org/10.1145/272991.272995)
Seeded deterministic RNG — reproducibility guarantee.

**[A-extra]** McGuirl M.R., Volkening A., Sandstede B. (2020). TDA of zebrafish patterns. *PLoS Comput. Biol.*, 16(3), e1007679. DOI: [10.1371/journal.pcbi.1007679](https://doi.org/10.1371/journal.pcbi.1007679)
TDA gamma measurement on biological patterning — γ_WT = +1.043.

---

## B. Monographs and Textbooks

**[B1]** Hairer E., Norsett S.P., Wanner G. (1993). *Solving ODEs I: Nonstiff Problems*. Springer. DOI: [10.1007/978-3-540-78862-1](https://doi.org/10.1007/978-3-540-78862-1)
Explicit Euler and Runge-Kutta — ODE integration.

**[B2]** Björck Å. (1996). *Numerical Methods for Least Squares Problems*. SIAM. DOI: [10.1137/1.9781611971484](https://doi.org/10.1137/1.9781611971484)
Deterministic least-squares regression.

**[B3]** Kelso J.A.S. (1995). *Dynamic Patterns: The Self-Organization of Brain and Behavior*. MIT Press. ISBN: 978-0262611312.
Coordination dynamics and metastability — conceptual foundation.

---

## S. Standards and Specifications

**[S1]** NeurIPS Paper Checklist (2024). https://neurips.cc/public/guides/PaperChecklist
Mandatory reproducibility checklist.

**[S2]** ACM Artifact Review and Badging v1.1 (2020). https://www.acm.org/publications/policies/artifact-review-and-badging-current
Artifact badges policy.

**[S3]** PyTorch Randomness and Determinism (2024). https://pytorch.org/docs/stable/notes/randomness.html
Deterministic algorithms documentation.

---

## Cross-Platform Reference Network

| Source | bnsyn | neosynaptex | MFN | agents | CA1 | mlsdm |
|--------|:-----:|:-----------:|:---:|:------:|:---:|:-----:|
| Brette & Gerstner 2005 | **x** | **x** | | | | |
| Beggs & Plenz 2003 | **x** | **x** | | **x** | | |
| Bak+ 1987 | **x** | **x** | **x** | | | |
| Buzsáki & Wang 2012 | **x** | **x** | | **x** | | |
| Tognoli & Kelso 2014 | **x** | **x** | | **x** | | |
| Clauset+ 2009 | **x** | **x** | | | | |
| Wilting & Priesemann 2018 | **x** | **x** | | | | |
| McGuirl+ 2020 | **x** | **x** | **x** | **x** | | |
| Turrigiano 2012 | **x** | | **x** | | | **x** |
| Benna & Fusi 2016 | **x** | | | | | **x** |
| Hopfield 1982 | **x** | | | | | **x** |

---

## Verification Protocol

All DOIs verified via CrossRef API or doi.org resolution on 2026-03-31.
BibTeX entries with full metadata in `bibliography/bnsyn.bib` (canonical source of truth).
To verify: `curl -sL "https://doi.org/[DOI]" -o /dev/null -w "%{http_code}"` → expect `302` or `200`.

**Policy:** Normative scientific claims cite Tier-F or Tier-A sources only. Architectural/process claims may cite Tier-B or Tier-S.

---

## Citation

```bibtex
@software{vasylenko2026_bnsyn,
  author  = {Vasylenko, Yaroslav},
  title   = {BN-Syn: Phase-Controlled Emergent Dynamics},
  year    = {2026},
  url     = {https://github.com/neuron7xLab/bnsyn-phase-controlled-emergent-dynamics},
  version = {1.0.0}
}
```
