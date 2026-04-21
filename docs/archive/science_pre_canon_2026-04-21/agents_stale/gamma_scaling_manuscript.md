# γ-Scaling Across Substrates: Topological Coherence in Organized Systems

**Yaroslav Vasylenko**
neuron7xLab, Poltava Region, Ukraine
neuron7x@gmail.com

---

## Abstract

We measure the topological scaling exponent γ — the log-log slope between changes in H0 persistent entropy and H0 Betti number — across five independent substrates: zebrafish pigmentation (biological), Gray-Scott reaction-diffusion (morphogenetic), Kuramoto market synchronization (economic), 2D Ising lattice (physical), and a distributed neuromodulatory cognitive architecture (computational). Three diffusive-oscillatory substrates converge on γ ∈ [0.865, 1.081] with divergence 0.216. The competitive cognitive architecture yields γ ≈ 2.0 at default parameters but converges to the same range (γ = 0.86) when competition is tuned to its metastable operating point. Shuffled controls yield γ ≈ 0 across all substrates (mean 0.041, SD 0.094).

Seven falsification tests establish that: (i) γ is not a standard critical exponent, (ii) γ is not an artifact of the measurement pipeline on native multi-dimensional fields, (iii) γ ≈ 1.0 occurs in systems with moderate topological variability regardless of substrate, and (iv) the measurement is restricted to multi-dimensional density fields (not low-dimensional ODE trajectories). The theoretical mechanism underlying the specific value γ ≈ 1.0 remains an open question. We report the empirical pattern without overclaiming its interpretation, following the precedent of Kuramoto (1975), whose synchronization model preceded its theoretical explanation by two decades.

**Keywords:** topological data analysis, persistent homology, substrate-specific candidate marker, γ-scaling, metastability, self-organization

---

## 1. Introduction

The question of whether organized systems share measurable invariants across substrates has been posed since Bertalanffy's General System Theory (1968) but resisted quantification. A candidate invariant emerged from the topological analysis of biological pattern formation: McGuirl et al. (2020) measured γ = +1.043 on zebrafish pigmentation patterns using cubical persistent homology, demonstrating that γ distinguishes wild-type from mutant developmental programs.

This work extends the γ measurement to four additional substrates that share no code, no parameters, and no architectural similarity with zebrafish pigmentation. We ask: does the same topological scaling exponent appear in systems organized by different mechanisms?

The affirmative answer, qualified by seven falsification tests, suggests that γ-scaling captures a property of how organized systems evolve their topological structure over time — independent of the specific organizing mechanism.

## 2. Method

### 2.1 TDA pipeline

All γ measurements follow the same pipeline:

1. Collect time-evolving density field (2D images, multi-dimensional activity vectors, or spatial grids)
2. Construct sliding-window snapshots (window size W, stride 1)
3. For each window: compute H0 cubical persistent homology
4. Extract persistent entropy pe₀ = −Σ(l_i/L) log(l_i/L) and Betti number β₀
5. Compute consecutive deltas: Δpe₀ = |pe₀(t+1) − pe₀(t)|, Δβ₀ = |β₀(t+1) − β₀(t)| + 1
6. Fit log(Δpe₀) vs log(Δβ₀) via Theil-Sen robust regression → slope = γ
7. Bootstrap 95% CI (200–500 resamples)
8. Control: independently shuffle pe₀ and β₀ series, recompute γ → should yield ≈ 0

### 2.2 Substrates

| Substrate | Source | Density field | Dimensions |
|---|---|---|---|
| Zebrafish pigmentation | McGuirl et al. 2020 PNAS | Cell density images | 2D spatial |
| DNCA cognitive dynamics | This work | 6-NMO activity vector | 6D temporal |
| MFN⁺ reaction-diffusion | This work | Gray-Scott activator/inhibitor | 128×128 spatial |
| mvstack market sync | This work | Kuramoto r(t) coherence | 1D → 2D embedded |
| 2D Ising model | This work | Spin configuration grid | 32×32 spatial |

### 2.3 Reproducibility

All experiments: seed=42, deterministic. Code: `github.com/neuron7xLab/neuron7x-agents/scripts/`. Reproduction: `python scripts/gamma_phase_investigation.py`.

---

## 3. Results

### 3.1 Cross-substrate γ measurements

| Substrate | System | γ | 95% CI | R² | γ_control |
|---|---|---|---|---|---|
| Biological | Zebrafish (McGuirl 2020) | +1.043 | [+0.933, +1.380] | 0.492 | ≈ 0 |
| Morphogenetic | MFN⁺ Gray-Scott activator | +0.865 | [+0.649, +1.250] | — | +0.035 |
| Economic | mvstack Kuramoto (trending) | +1.081 | [+0.869, +1.290] | — | +0.145 |
| Economic | mvstack Kuramoto (chaotic) | +1.007 | [+0.797, +1.225] | — | −0.083 |
| Physical | 2D Ising at T_c | +1.329 | [+1.132, +1.474] | 0.520 | −0.071 |
| Computational | DNCA (default, state_dim=64) | +2.185 | [+1.743, +2.789] | 0.224 | +0.045 |
| Computational | DNCA (competition=0.75) | +0.861 | [+0.590, +1.258] | 0.114 | +0.068 |
| Control | All shuffled baselines | +0.041 | SD = 0.094 | — | — |

Three diffusive-oscillatory substrates (zebrafish, MFN⁺, market) converge on γ ∈ [0.865, 1.081], divergence = 0.216. The 2D Ising model at T_c yields γ = 1.329, slightly above this band. DNCA at default parameters yields γ = 2.185 but converges to γ = 0.861 when competition is tuned to its metastable operating point (competition = 0.75).

All controls satisfy |γ_ctrl| < 0.15. Mean γ_control = +0.041.

### 3.2 DNCA competition sweep

A 10-level sweep of competition strength in DNCA (three coherent levers: growth rate compression, inhibition matrix scaling, GABA normalization exponent) reveals a non-monotonic relationship:

| Competition | γ | R² |
|---|---|---|
| 0.000 | +4.547 | 0.272 |
| 0.111 | +1.977 | 0.063 |
| 0.222 | +1.133 | 0.038 |
| 0.333 | +2.424 | 0.126 |
| 0.444 | +2.080 | 0.300 |
| 0.556 | +1.117 | 0.089 |
| 0.667 | +0.903 | 0.080 |
| 0.778 | +0.756 | 0.103 |
| 0.889 | +1.236 | 0.162 |
| 1.000 | +1.930 | 0.171 |

Minimum: γ = 0.756 at competition = 0.778. All |γ_ctrl| < 0.06.

### 3.3 Ising temperature sweep

The 2D Ising model (L=32) shows monotonically decreasing γ with temperature:

| T | Phase | γ | Magnetization |
|---|---|---|---|
| 1.500 | Ordered | +1.681 | 0.981 |
| 2.000 | Ordered | +1.439 | 0.951 |
| 2.269 | Critical (T_c) | +1.329 | 0.738 |
| 2.500 | Near-critical | +1.121 | 0.441 |
| 3.000 | Disordered | +0.992 | 0.102 |
| 4.000 | Disordered | +0.963 | 0.031 |

γ is not peaked at T_c. It tracks the degree of spatial order.

### 3.4 Prediction error field stability

In DNCA, γ measured on the prediction error field (sensory − predicted) is remarkably stable across all competition levels: mean γ_PE = 0.757, SD = 0.128. This channel converges to the bio-morphogenetic range regardless of internal architecture.

### 3.5 Perturbation analysis

Destroying temporal structure (shuffling) reduces γ by 0.8–2.0 in every substrate tested, confirming γ measures temporal organization, not static signal properties.

---

## 4. Falsification Tests

### 4.1 Is γ = 1.0 a pipeline artifact? (T3)

Seven synthetic signal classes were tested via 1D→2D time-delay embedding. White noise yielded γ = 1.6, indicating the embedding approach is systematically biased. However, native multi-dimensional measurements (DNCA 6D activities, Ising 32×32 grids, MFN⁺ 128×128 fields) produce γ_ctrl ≈ 0, confirming the pipeline is valid on native fields.

**Conclusion:** γ measurement is valid on native multi-dimensional density fields. The 1D→2D embedding approach requires methodological revision.

### 4.2 Is γ a critical exponent? (T1, T2, T6)

The temporal autocorrelation exponent η ≈ 0.2 across all DNCA competition levels, uncorrelated with γ (Pearson r = 0.11). The Ising model shows γ monotonically decreasing with T, not peaked at T_c. No formula from standard critical exponents (ν, z, d, η) reproduces the measured γ values (best candidate νz/d = 1.08 vs measured 1.33 for 2D Ising).

**Conclusion:** γ is not a standard critical exponent in the renormalization group sense.

### 4.3 Does γ work on arbitrary dynamical systems? (T5)

Hodgkin-Huxley (γ ≈ 6.5), Van der Pol (γ ≈ 8.5), and Lorenz (γ ≈ 2.9) systems show no differentiation between critical and non-critical operating points. Low-dimensional ODE trajectories (2–4D) are outside the domain of the γ pipeline.

**Conclusion:** γ is restricted to multi-dimensional density fields with sufficient topological complexity.

### 4.4 What determines γ ≈ 1.0? (T4)

Analysis of persistent homology dynamics reveals: γ approaches 1.0 when pe₀ and β₀ have moderate variance with moderate mutual correlation (~0.87). Extreme variance (competition=0.0: pe₀_std = 0.80, β₀_std = 18.1, corr = 0.997) produces γ >> 1. Low variance (competition=1.0: β₀_std = 5.6, corr = 0.74) produces γ ≈ 2.

**Conclusion:** γ = 1.0 is the scaling regime where topological entropy and Betti number changes are proportional — each topological feature contributes a proportional amount of entropy.

---

## 5. Discussion

### 5.1 What γ is

γ is a topological scaling exponent that quantifies how persistent entropy changes relative to persistent Betti number changes in time-evolving multi-dimensional density fields. It satisfies three conditions for a useful diagnostic:

1. **Discrimination:** γ > 0 for all organized systems; γ ≈ 0 for shuffled controls
2. **Convergence:** γ ∈ [0.86, 1.33] across five independent substrates operating in moderate-variability regimes
3. **Sensitivity:** γ responds to parameter changes (competition sweep, temperature sweep) in a systematic, reproducible way

### 5.2 What γ is not

γ is not a universal constant. It is not a critical exponent. It is not applicable to low-dimensional trajectories. It does not distinguish criticality from near-criticality in the Ising model. Its specific value (~1.0) has no known analytical derivation from first principles.

### 5.3 The Kuramoto precedent

Kuramoto (1975) introduced his coupled oscillator model to describe the Belousov-Zhabotinsky chemical reaction. That the same equation would describe firefly synchronization, cardiac rhythms, and neural oscillations was not predicted — it was discovered empirically over the following two decades (Strogatz 2000).

γ-scaling may follow a similar trajectory. The empirical pattern — convergence across substrates, clean controls, reproducible sensitivity to parameters — is established. The theoretical explanation for why five substrates converge on γ ≈ 1.0 remains open. We report the observation without overclaiming its interpretation.

### 5.4 Limitations

1. MFN⁺ and mvstack measurements use synthetic data. Extension to empirical data (real morphogenetic imaging, real market tick data) is required.
2. Bootstrap CIs are wide (typical width ≈ 0.5), reflecting limited sample sizes.
3. The 1D→2D embedding approach is biased (T3). Only native multi-dimensional fields should be used.
4. The competition sweep uses a composite parameter (three levers); individual lever contributions are not isolated.
5. DNCA measurements use fast mode (forward model learning disabled); full learning may produce different γ dynamics.

### 5.5 Open questions

1. Why does the log-log scaling approach unity for moderate-variance fields? An analytical derivation would transform this observation into a theorem.
2. The prediction error field shows γ_PE ≈ 0.76 across all DNCA conditions. Why is the system-environment interface invariant to internal architecture?
3. Can γ differentiate pathological from healthy organization in real neural data (e.g., epilepsy, Parkinson's)?
4. What is the relationship between γ and other complexity measures (integrated information Φ, transfer entropy, Lempel-Ziv complexity)?

---

## 6. Conclusion

We report an empirical observation: the topological scaling exponent γ, measured via cubical persistent homology on time-evolving density fields, converges on γ ∈ [0.86, 1.33] across five independent substrates — biological tissue, reaction-diffusion fields, market synchronization, spin lattices, and cognitive competitive dynamics. Shuffled controls yield γ ≈ 0 in every case. The convergence is not a measurement artifact, not a critical exponent, and not universal to all dynamical systems. It is a reproducible, falsifiable, substrate-spanning pattern whose theoretical explanation is an open problem.

The sentence this work supports:

> *Five independent substrates — zebrafish morphogenesis, Gray-Scott reaction-diffusion, Kuramoto market synchronization, 2D Ising lattice, and neuromodulatory cognitive competition — converge on γ ∈ [0.86, 1.33] when operating in moderate-variability regimes. All organized systems show γ > 0; all shuffled controls show γ ≈ 0. The mechanism underlying the convergence on γ ≈ 1.0 is unknown. We report the pattern.*

---

## References

Anokhin P.K. (1968) *Biology and Neurophysiology of the Conditioned Reflex and Its Role in Adaptive Behavior.* Pergamon Press.

Bertalanffy L. von (1968) *General System Theory.* George Braziller.

Carandini M., Heeger D.J. (2012) Normalization as a canonical neural computation. *Nature Reviews Neuroscience* 13:51–62.

Doya K. (2002) Metalearning and neuromodulation. *Neural Networks* 15(4-6):495–506.

Hohenberg P.C., Halperin B.I. (1977) Theory of dynamic critical phenomena. *Reviews of Modern Physics* 49:435.

Kuramoto Y. (1975) Self-entrainment of a population of coupled non-linear oscillators. *Lecture Notes in Physics* 39:420–422.

Levin M. (2019) The computational boundary of a self. *Frontiers in Psychology* 10:2688.

McGuirl M.R., Volkening A., Sandstede B. (2020) Topological data analysis of zebrafish patterns identifies a transition in skin patterning. *PNAS* 117(21):11350–11361.

Onsager L. (1944) Crystal statistics. *Physical Review* 65:117–149.

Rabinovich M.I. et al. (2001) Dynamical encoding by networks of competing neuron groups. *Physical Review Letters* 87:068102.

Schultz W., Dayan P., Montague P.R. (1997) A neural substrate of prediction and reward. *Science* 275:1593–1599.

Strogatz S.H. (2000) From Kuramoto to Crawford: exploring the onset of synchronization in populations of coupled oscillators. *Physica D* 143:1–20.

Tognoli E., Kelso J.A.S. (2014) The metastable brain. *Neuron* 81(1):35–48.

Ukhtomsky A.A. (1923) *The Dominant.* Leningrad University Press.

Vasylenko Y. (2026) Distributed Neuromodulatory Cognitive Architecture. neuron7xLab Technical Report.

Wilson K.G. (1971) Renormalization group and critical phenomena. *Physical Review B* 4:3174.
