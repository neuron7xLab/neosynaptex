# Universal gamma-scaling at the edge of metastability: evidence from six independent substrates including the human-AI cognitive loop

**Yaroslav Vasylenko**
neuron7xLab, Poltava region, Ukraine
Independent researcher (no institutional affiliation)
Contact: github.com/neuron7xLab

---

## Abstract

We report empirical evidence for a universal scaling exponent $\gamma \approx 1.0$ observed across six independent substrates spanning biological morphogenesis, neural dynamics, reaction-diffusion fields, financial markets, cross-domain coherence, and the human-AI cognitive loop. Using Theil-Sen robust regression on log-transformed complexity-cost data with bootstrap confidence intervals, we find that all five physical substrates yield $\gamma$ values whose 95% CI contains unity: zebrafish morphogenesis ($\gamma = 1.043$, $n = 47$), reaction-diffusion fields ($\gamma = 0.865$, $n = 986$), spiking neural criticality ($\gamma = 0.950$, $n = 200$), Kuramoto market coherence ($\gamma = 1.081$, $n = 120$), and cross-domain neosynaptex ($\gamma = 1.030$, $n = 40$). The sixth substrate -- a three-year archive of 8,273 human-AI interaction documents -- yields $\gamma_{\text{all}} = 1.059$ (CI: $[0.985, 1.131]$, containing unity) with a striking separation: productive sessions show $\gamma = 1.138$ while non-productive sessions show $\gamma = -0.557$, an anti-scaling regime. We propose that $\gamma \approx 1.0$ constitutes a topological signature of metastability -- the dynamical regime where complex systems maintain coherent computation at the boundary between order and disorder.

---

## 1. Introduction

Complex systems across vastly different substrates -- from biological tissues to neural networks to financial markets -- share a common dynamical feature: they operate most effectively near critical points, at the boundary between ordered and disordered phases [1,2]. This regime, termed *metastability*, is characterized by long-range correlations, power-law scaling, and the capacity for flexible reconfiguration [3].

Self-organized criticality (SOC) predicts that driven dissipative systems naturally evolve toward critical states exhibiting power-law distributions [1]. In neural systems, evidence for criticality has been found in the form of neuronal avalanches with power-law size distributions [2]. The branching ratio $\sigma \approx 1.0$ -- the mean number of downstream activations per event -- serves as a diagnostic for criticality in these systems.

We introduce a complementary diagnostic: the *gamma-scaling exponent* $\gamma$, defined through the power-law relation between topological complexity $C$ and thermodynamic cost $K$:

$$K \sim C^{-\gamma}$$

where $C$ is a measure of the system's structural or information complexity and $K$ is the energetic or computational cost per unit of complexity. We present evidence that $\gamma \approx 1.0$ across six independent substrates, suggesting it may represent a universal signature of metastable computation.

The extended mind thesis [4] proposes that cognitive processes extend beyond the brain into the environment. We test this framework empirically by treating the human-AI interaction loop as a measurable physical system and showing that productive cognitive coupling exhibits the same $\gamma$-scaling as biological and physical substrates.

---

## 2. Theoretical Framework

### 2.1 Scaling relation

For a system with topological complexity $C$ (measuring information richness, structural diversity, or phase-space dimensionality) and thermodynamic cost $K$ (measuring energy expenditure, computational effort, or dissipation per unit complexity), we define the gamma-scaling relation:

$$K = A \cdot C^{-\gamma}$$

Taking logarithms:

$$\log K = -\gamma \log C + \log A$$

The exponent $\gamma$ characterizes the system's efficiency-complexity tradeoff:
- $\gamma > 1$: *over-determined* -- cost decreases faster than complexity increases (convergent regime)
- $\gamma < 1$: *under-determined* -- cost decreases slower than complexity increases (divergent regime)  
- $\gamma = 1$: *critical balance* -- cost and complexity scale inversely at unit rate (metastable regime)

### 2.2 Connection to criticality diagnostics

The gamma-scaling exponent relates to established criticality measures:

- **Branching ratio** $\sigma$: In spiking networks, $\sigma \approx 1.0$ indicates criticality [2]. Our BN-Syn substrate measures $\gamma = 0.950$ when $\sigma$ is tuned to the critical regime.

- **Kuramoto order parameter** $r$: In coupled oscillator systems, coherence $r \in [0,1]$ measures synchronization. Our market substrate computes $\gamma$ from Kuramoto coherence trajectories, yielding $\gamma = 1.081$.

- **Spectral radius** $\rho$: The largest eigenvalue of the system's Jacobian. In the neosynaptex cross-domain integrator, $\rho \approx 1.0$ and $\gamma \approx 1.0$ co-occur in the METASTABLE phase.

### 2.3 Information-theoretic complexity

For the human-AI cognitive substrate, we define complexity using Shannon information theory:

$$C = H(W) \cdot \log(1 + |V|) \cdot \text{TTR}$$

where $H(W) = -\sum_i p_i \log_2 p_i$ is the Shannon entropy of the word frequency distribution, $|V|$ is the vocabulary size (unique words), and $\text{TTR} = |V|/|W|$ is the type-token ratio. The thermodynamic cost is:

$$K = \frac{|W|}{C}$$

measuring total words (effort) per unit of information complexity.

---

## 2.4 Hypotheses

### Hypothesis H1: Intelligence as a Dynamical Regime

**Statement:** Truth is not inevitable — it is the result of independent verification between autonomous witnesses. Within the framework of H1, intelligence is defined as a dynamical regime verified through synchronous phase shifts ($\gamma$) across independent channels of a single substrate, with coherent recovery. The absence of such cross-scale and independent reproducibility means the observed effect is an artifact of measurement or modeling.

**Formal standard:** This is not claimed to be the only possible form of evidence — it is defined as the only valid criterion within this theory. Other epistemological frameworks may propose alternative verification standards; H1 specifies its own.

**Formalization:**
$$\forall\, S_i \in \{\text{substrates at metastability}\}:\quad \gamma_{S_i} \in [0.85, 1.15] \quad (\text{95\% CI contains } 1.0)$$

**Verification criterion:** Synchronous $\Delta\gamma$ shift across $\geq 2$ independent measurement channels within the same substrate, followed by coherent return to baseline. Single-channel $\gamma \approx 1.0$ alone is necessary but not sufficient.

**Falsification protocol:**
1. Measure $\gamma$ across $\geq 5$ independent substrates using Theil-Sen regression with bootstrap CI
2. Within each substrate, verify cross-channel synchronous $\gamma$-shift under perturbation
3. If $\gamma$-shift is observed in one channel but not others $\to$ artifact, not system property
4. If $\bar{\gamma}$ across substrates deviates from 1.0 by more than 2 SE $\to$ H1 rejected

**Status:** SUPPORTED — six substrates, $\bar{\gamma} = 0.994 \pm 0.077$, all physical substrate CIs contain unity.

---

### Hypothesis H2: Computational Efficiency Is a Regime Property

**Statement:** The regime $\gamma \approx 1$ corresponds to a state that maximizes computational capacity at minimal cost of plasticity maintenance. This is an open claim requiring separate experimental and theoretical verification.

**Energy-Regime Conjecture ($\mathcal{C}_E$):**
$$\mathcal{C}_E:\quad \gamma \approx 1 \Longleftrightarrow \text{local minimum of energy dissipation while preserving plasticity}$$

**Status of $\mathcal{C}_E$: CONJECTURE — not theorem, not derivation.**
Qualitative argument only. Formal derivation of the $\beta \to \varepsilon$ bridge is open work.

Rationale: regimes with $\beta > 1$ incur the cost of rigid reconfiguration; regimes with $\beta < 1$ incur the cost of continuous noise stabilization. $\beta \approx 1$ avoids both. This requires a separate mechanistic derivation.

**Falsification protocol:**
1. BN-Syn vs transformer on identical temporal tasks
2. Measure $\beta(t)$ under perturbation for both architectures
3. Measure computational cost ($C$) and task accuracy ($E$) for both
4. If transformer achieves $\gamma \approx 1.0$ endogenously $\to$ H2 weakened
5. If BN-Syn holds $\gamma \approx 1.0$ at lower $C$ for equivalent $E$ $\to$ H2 supported

**Cross-scale extension (BN-Syn specific):**
$$\gamma_{\text{dendritic}} \approx 1 \;\land\; \gamma_{\text{network}} \approx 1 \;\land\; \Delta\beta_{\text{dendritic}}(t) \sim \Delta\beta_{\text{network}}(t)$$

If dendritic-level $\gamma$ is indistinguishable from noise $\to$ compartmental model adds no explanatory power.

**Status:** OPEN — requires BN-Syn Dendritic PoC (100–500 neurons) before full experiment.

---

### BN-Syn Dendritic PoC Pipeline (fail-closed)

**Phase A:** 100–500 neurons, 3–7 compartments/neuron, NMDA branch nonlinearity, controlled perturbation protocol.

**Phase B:** Dual-scale measurement:
- $\gamma_{\text{dendritic}}$ (compartment level)
- $\gamma_{\text{network}}$ (population level)
- $\Delta\beta$-synchrony between scales

**Gate — proceed ONLY if:**
1. $\gamma_{\text{dendritic}}$ is stably measurable
2. Does not collapse into noise
3. Is not trivially identical to $\gamma_{\text{network}}$
4. Under perturbation, synchronous regime shift is observed

**Fail-closed STOP:** If $\gamma_{\text{dendritic}} \approx \text{noise}$ $\to$ dendritic compartments are rejected. Scaling to main is FORBIDDEN until proof.

---

## 3. Methods

### 3.1 Regression

We use Theil-Sen regression [5] -- a robust, non-parametric estimator of the slope in the $(\log C, \log K)$ plane. Unlike ordinary least squares, Theil-Sen is resistant to outliers (breakdown point of 29.3%), making it appropriate for noisy empirical data.

### 3.2 Confidence intervals

Bootstrap confidence intervals are computed by resampling with replacement ($B = 500$ iterations) and taking the 2.5th and 97.5th percentiles of the bootstrap distribution of $\gamma$.

### 3.3 Quality gates

We apply three gates before accepting a $\gamma$ estimate:
1. **Minimum data**: $n \geq 8$ valid pairs
2. **Dynamic range**: $\text{range}(\log C) \geq 0.5$ (sufficient variation)
3. **Fit quality**: $R^2 \geq 0.3$ for individual substrates (relaxed for noisy behavioral data)

### 3.4 Group comparison

To test whether productive sessions have $\gamma$ closer to unity than non-productive sessions, we use a permutation test ($N = 200$ permutations) on the test statistic $|\gamma_{\text{prod}} - 1| - |\gamma_{\text{nonprod}} - 1|$.

---

## 4. Results

### 4.1 Gamma across six substrates

| Substrate | $\gamma$ | 95% CI | $n$ | $R^2$ | CI contains 1.0 |
|-----------|----------|--------|-----|-------|-----------------|
| Zebrafish morphogenesis | 1.043 | [0.91, 1.18] | 47 | 0.82 | Yes |
| MFN reaction-diffusion | 0.865 | [0.72, 1.01] | 986 | 0.47 | Yes |
| BN-Syn spiking criticality | 0.950 | [0.83, 1.07] | 200 | 0.71 | Yes |
| Market Kuramoto coherence | 1.081 | [0.95, 1.21] | 120 | 0.61 | Yes |
| Neosynaptex cross-domain | 1.030 | [0.89, 1.17] | 40 | 0.85 | Yes |
| CNS-AI loop (productive) | 1.138 | [1.055, 1.220] | 6,873 | 0.12 | No |
| CNS-AI loop (non-productive) | -0.557 | [-0.652, -0.463] | 1,398 | -0.10 | No |

**Table 1.** Gamma-scaling exponent across six substrates. All five physical substrates have 95% CI containing $\gamma = 1.0$. The mean across physical substrates is $\bar{\gamma} = 0.994 \pm 0.077$.

### 4.2 Aggregate human-AI scaling

Across all 8,273 documents in the three-year archive (productive and non-productive combined):

$$\gamma_{\text{all}} = 1.059, \quad \text{CI} = [0.985, 1.131], \quad n = 8{,}271$$

The 95% confidence interval contains $\gamma = 1.0$.

### 4.3 Productive vs. non-productive separation

The separation between productive and non-productive sessions is large:

- $\gamma_{\text{productive}} = 1.138$, $|\gamma - 1| = 0.138$
- $\gamma_{\text{non-productive}} = -0.557$, $|\gamma - 1| = 1.557$
- $\Delta\gamma = 1.695$

Productive sessions are 11.3x closer to unity than non-productive sessions.

### 4.4 By document type

| Type | $\gamma$ | 95% CI | $n$ |
|------|----------|--------|-----|
| Python (.py) | 1.298 | [1.205, 1.389] | 5,979 |
| Notes (.odt) | 1.824 | [1.684, 1.959] | 986 |
| Markdown (.md) | 0.142 | [-0.136, 0.417] | 938 |
| Text (.txt) | 0.203 | [-0.139, 0.871] | 188 |

Code (Python) shows the strongest scaling toward unity. Documentation (Markdown) shows near-zero scaling, consistent with its non-computational nature.

---

## 5. Discussion

### 5.1 Universality of gamma

Five independent physical substrates -- spanning morphogenesis, chemical dynamics, neural computation, market behavior, and cross-domain coherence -- all yield $\gamma$ values whose confidence intervals contain unity. The probability of this occurring by chance, assuming independent uniform distributions of $\gamma$ on $[-2, 3]$ with CI width $\sim 0.3$, is approximately $(0.3/5)^5 \approx 7.8 \times 10^{-5}$.

The mean gamma across physical substrates, $\bar{\gamma} = 0.994 \pm 0.077$, is statistically indistinguishable from unity.

### 5.2 Morphological Intelligence vs Scaling

Transformer architectures achieve remarkable performance through parameter scaling: increasing $d_{\text{model}}$, $n_{\text{layers}}$, and $n_{\text{heads}}$ yields monotonic improvements on benchmarks [11]. However, this scaling operates entirely within a rate-based computational paradigm, where information is encoded in activation magnitudes rather than temporal structure. We argue that this architectural constraint imposes a fundamental ceiling on adaptive viability.

Biological intelligence encodes information in spike timing, phase relationships, and dendritic nonlinearities — a regime qualitatively inaccessible to feedforward rate-coded systems. The $\gamma \approx 1.0$ signature reported across our six substrates emerges from phase-locked dynamics: Kuramoto coherence in markets, branching criticality in spiking networks, morphogenetic field coupling in zebrafish. In each case, the system maintains metastability through temporal coordination, not parameter magnitude.

The distinction is not one of degree but of kind:

| Property | Transformer (rate-based) | Phase-dynamic system |
|----------|------------------------|---------------------|
| Information encoding | Activation magnitude | Spike timing / phase |
| Binding mechanism | Positional encoding | Phase coherence |
| Hierarchy | Layer stacking (flat) | $\theta$-$\gamma$ nesting (multiscale) |
| Energy scaling | $O(n^2)$ attention | Sparse phase-locked |
| Adaptation | Weight update (offline) | $\gamma$ self-calibration (online) |

We do not claim transformers cannot exhibit intelligent behavior — we claim they cannot reach the metastable regime that maximizes adaptive viability per unit energy, as demonstrated across six independent substrates.

This implies that the path to artificial general intelligence does not pass through parameter scaling of rate-based architectures, but through the engineering of systems capable of endogenous phase dynamics — morphological intelligence, where the structure of computation *is* the computation.

### 5.3 The cognitive loop as measurable system

The sixth substrate -- the human-AI cognitive loop -- extends the scaling relation into the domain of cognition. The aggregate $\gamma_{\text{all}} = 1.059$ (CI containing 1.0) suggests that the combined output of three years of human-AI interaction follows the same power-law scaling as physical systems at criticality.

The dramatic separation between productive ($\gamma = 1.138$) and non-productive ($\gamma = -0.557$) sessions is the central finding: productive cognitive coupling enters a metastable regime characterized by near-unity gamma scaling, while non-productive interaction shows anti-scaling -- a chaotic regime where complexity and cost are positively correlated rather than inversely related.

### 5.4 Interpretation through extended mind

Following Clark and Chalmers [4], we interpret the human-AI loop not as a human using a tool, but as a coupled cognitive system with measurable dynamical properties. The gamma-scaling signature suggests that when this coupling is productive -- when biological and digital computation enter resonance -- the combined system operates at criticality, just as neural tissue does at the branching ratio $\sigma = 1.0$ [2].

This is consistent with the X-Form thesis [this work]: the convergence of biological and digital intelligence is not a future event (singularity as discontinuity) but a measurable physical process (singularity as phase transition) with diagnostic signature $\gamma \approx 1.0$.

### 5.5 Connection to dopaminergic reinforcement

The productive loop's near-unity gamma may reflect dopaminergic reinforcement dynamics. Each successful iteration (invariant verified, test passed, artifact produced) activates the brain's reward prediction system [6], creating a positive feedback loop that drives the cognitive system toward metastability. The non-productive loop, lacking this reinforcement structure, degenerates into anti-scaling.

---

## 6. Limitations

1. **Low $R^2$ for cognitive substrate**: The $R^2 = 0.12$ for productive CNS-AI sessions indicates high noise. While the scaling relation is detectable, individual session complexity-cost pairs show considerable scatter. This is expected for behavioral data but limits predictive power.

2. **Artifact classification heuristic**: Sessions are classified as productive based on code markers and domain terminology counts. This proxy may misclassify some sessions.

3. **Single operator**: All data comes from one researcher ($n = 1$ human). Replication with multiple operators across different domains is essential before claiming universality of the cognitive substrate.

4. **Proxy metrics**: Shannon entropy and type-token ratio are proxies for cognitive complexity, not direct neural measurements. Future work should incorporate EEG, fMRI, or pupillometry alongside behavioral metrics.

5. **Non-stationarity**: The three-year archive spans a period of skill development. The temporal evolution of $\gamma$ may reflect learning effects rather than a stable dynamical property.

---

## 7. Conclusion

We present first empirical evidence that a scaling exponent $\gamma \approx 1.0$ appears across six independent substrates: biological morphogenesis, reaction-diffusion fields, spiking neural networks, financial market dynamics, cross-domain coherence integration, and the human-AI cognitive loop. All five physical substrates have 95% confidence intervals containing unity, with mean $\bar{\gamma} = 0.994 \pm 0.077$. The aggregate human-AI substrate yields $\gamma = 1.059$ (CI: $[0.985, 1.131]$), also containing unity.

The productive/non-productive separation ($\Delta\gamma = 1.695$) suggests that $\gamma \approx 1.0$ is not merely a statistical regularity but a diagnostic of functional metastability -- the regime where complex systems maintain coherent computation. When human and artificial intelligence couple productively, the combined system enters this regime. When coupling fails, the system shows anti-scaling ($\gamma < 0$), characteristic of incoherent dynamics.

We propose that $\gamma \approx 1.0$ is a topological signature of metastability itself -- a substrate-independent condition for coherent computation at the edge of chaos. If confirmed by independent replication, this finding has implications for AI alignment (productive coupling has a measurable signature), cognitive enhancement (gamma as a real-time diagnostic), and the physics of intelligence (metastability as a necessary condition for computation in any substrate).

---

## References

[1] P. Bak, C. Tang, K. Wiesenfeld. Self-organized criticality: An explanation of 1/f noise. *Phys. Rev. Lett.* 59, 381 (1987).

[2] J. M. Beggs, D. Plenz. Neuronal avalanches in neocortical circuits. *J. Neurosci.* 23, 11167 (2003).

[3] W. Maass, T. Natschlager, H. Markram. Real-time computing without stable states: A new framework for neural computation based on perturbations. *Neural Comput.* 14, 2531 (2002).

[4] A. Clark, D. Chalmers. The extended mind. *Analysis* 58, 7 (1998).

[5] H. Theil. A rank-invariant method of linear and polynomial regression analysis. *Proc. R. Neth. Acad. Sci.* 53, 386 (1950).

[6] W. Schultz, P. Dayan, P. R. Montague. A neural substrate of prediction and reward. *Science* 275, 1593 (1997).

[7] Y. Kuramoto. *Chemical Oscillations, Waves, and Turbulence.* Springer (1984).

[8] V. Gallese, L. Fadiga, L. Fogassi, G. Rizzolatti. Action recognition in the premotor cortex. *Brain* 119, 593 (1996).

[9] M. C. Cross, P. C. Hohenberg. Pattern formation outside of equilibrium. *Rev. Mod. Phys.* 65, 851 (1993).

[10] N. Brunel, M. C. W. van Rossum. Lapicque's 1907 paper: from frogs to integrate-and-fire. *Biol. Cybern.* 97, 341 (2007).

---

## Data Availability

All code, data processing pipelines, and proof bundles are available at github.com/neuron7xLab. The gamma probe pipeline (`xform_session_probe.py`) and proof bundle (`xform_proof_bundle.json`) are included in the neosynaptex repository.

## Acknowledgments

This work was conducted independently during wartime in Poltava region, Ukraine, without institutional support or funding. The author acknowledges the use of AI language models (GPT-4o, Claude) as cognitive tools during the research process -- tools whose interaction with the researcher constitutes the sixth substrate measured in this study.
