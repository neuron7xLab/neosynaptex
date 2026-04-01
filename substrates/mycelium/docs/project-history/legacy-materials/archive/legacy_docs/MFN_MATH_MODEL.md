# Mathematical Model Formalization — MyceliumFractalNet v4.1

This document provides a rigorous mathematical formalization of the three core components
of the MyceliumFractalNet system:

1. **Membrane Potentials** — Nernst/Goldman-Hodgkin-Katz electrochemistry
2. **Reaction-Diffusion Processes** — Turing morphogenesis activator-inhibitor dynamics
3. **Fractal Growth** — Iterated Function Systems and box-counting dimension analysis

All equations are presented with explicit parameter definitions, physical units,
valid ranges, and their mapping to the implementation in `src/mycelium_fractal_net/model.py`.

---

## 1. Membrane Potentials

### 1.1 Physical Background

Biological neurons maintain an electrical potential difference across their cell membrane,
driven by unequal distributions of ions (primarily K⁺, Na⁺, Cl⁻, Ca²⁺). The equilibrium
potential for a single ion species is described by the **Nernst equation**.

### 1.2 Nernst Equation

The equilibrium potential $E_X$ for ion species $X$ with valence $z$ is:

$$
E_X = \frac{RT}{zF} \ln\left(\frac{[X]_{\text{out}}}{[X]_{\text{in}}}\right)
$$

where:
- $R$ = Universal gas constant
- $T$ = Absolute temperature
- $z$ = Ion valence (signed integer)
- $F$ = Faraday constant
- $[X]_{\text{out}}$ = Extracellular ion concentration
- $[X]_{\text{in}}$ = Intracellular ion concentration

### 1.3 Parameter Table

| Parameter | Symbol | Value | Units | Valid Range | Physical Meaning |
|-----------|--------|-------|-------|-------------|------------------|
| Gas constant | $R$ | 8.314 | J/(mol·K) | (constant) | Thermodynamic constant |
| Faraday constant | $F$ | 96485.33 | C/mol | (constant) | Charge per mole electrons |
| Body temperature | $T$ | 310 | K | [273, 320] | Physiological temperature (~37°C) |
| Ion valence | $z$ | ±1, ±2 | – | {-2, -1, 1, 2} | K⁺=+1, Na⁺=+1, Cl⁻=−1, Ca²⁺=+2 |
| Concentration (out) | $[X]_{\text{out}}$ | varies | mol/L | ≥ 1e-6 | Extracellular concentration |
| Concentration (in) | $[X]_{\text{in}}$ | varies | mol/L | ≥ 1e-6 | Intracellular concentration |
| **RT/zF at 37°C, z=1** | – | 26.73 | mV | – | Nernst factor (natural log) |
| Time step | $\Delta t$ | 1e-4 | s | [1e-7, 1e-2] | Integration step (0.1 μs – 10 ms) |

**Biophysical Constraints (ENFORCED in code):**
- Temperature [273, 320] K covers hypothermic (0°C) to hyperthermic (47°C) limits
- Ion valence ∈ {-2, -1, 1, 2} covers biological ions (K⁺, Na⁺, Cl⁻, Ca²⁺, Mg²⁺)
- Concentration clamp ≥ 1e-6 mol/L prevents log(0) numerical errors

### 1.4 Physiological Reference Values

| Ion | $[X]_{\text{in}}$ (mM) | $[X]_{\text{out}}$ (mM) | $z$ | $E_X$ (mV) |
|-----|------------------------|-------------------------|-----|------------|
| K⁺ | 140 | 5 | +1 | ≈ −89 |
| Na⁺ | 12 | 145 | +1 | ≈ +65 |
| Cl⁻ | 4 | 120 | −1 | ≈ −89 |
| Ca²⁺ | 0.0001 | 2 | +2 | ≈ +129 |

### 1.5 Implementation Mapping

```
Code Location: src/mycelium_fractal_net/core/membrane_engine.py

Constants:
- R_GAS_CONSTANT = 8.314      # J/(mol·K)
- FARADAY_CONSTANT = 96485.33 # C/mol
- BODY_TEMPERATURE_K = 310.0  # K
- TEMPERATURE_MIN_K = 273.0   # K (hypothermic limit)
- TEMPERATURE_MAX_K = 320.0   # K (hyperthermic limit)
- ION_VALENCE_ALLOWED = (-2, -1, 1, 2)
- ION_CLAMP_MIN = 1e-6        # mol/L
- DT_MIN = 1e-7               # s (0.1 μs)
- DT_MAX = 1e-2               # s (10 ms)

Classes:
- MembraneConfig: Configuration with validated bounds
- MembraneEngine: Nernst computation with stability checks

Function: compute_nernst_potential(z_valence, concentration_out_molar, 
                                   concentration_in_molar, temperature_k)
Returns: Membrane potential in Volts

Numerical Stability:
- Ion concentrations clamped to min = 1e-6 mol/L (ION_CLAMP_MIN)
- Prevents log(0) and log(negative) errors
- Ion valence validated against allowed set
- Temperature validated against physiological range
```

### 1.6 Validation Invariants

1. **Physical bounds**: $-150 \text{ mV} \leq E_X \leq +150 \text{ mV}$ for physiological conditions
2. **Sign consistency**: If $[X]_{\text{out}} > [X]_{\text{in}}$ and $z > 0$, then $E_X > 0$
3. **No NaN/Inf**: Clamping ensures finite output for all positive inputs
4. **Verification**: K⁺ at standard concentrations yields $E_K \approx -89 \pm 2$ mV

---

## 2. Reaction-Diffusion Processes (Turing Morphogenesis)

### 2.1 Physical Background

Alan Turing (1952) proposed that biological pattern formation arises from
reaction-diffusion dynamics between a short-range **activator** and a long-range
**inhibitor**. This mechanism explains morphogenesis, zebra stripes, leopard spots,
and mycelial network formation.

### 2.2 Governing Equations

The activator-inhibitor system is described by coupled PDEs:

$$
\frac{\partial a}{\partial t} = D_a \nabla^2 a + f(a, i)
$$

$$
\frac{\partial i}{\partial t} = D_i \nabla^2 i + g(a, i)
$$

**MFN Implementation (simplified Turing model):**

$$
\frac{\partial a}{\partial t} = D_a \nabla^2 a + r_a \cdot a(1-a) - i
$$

$$
\frac{\partial i}{\partial t} = D_i \nabla^2 i + r_i \cdot (a - i)
$$

where:
- $a(x, y, t)$ = activator concentration field
- $i(x, y, t)$ = inhibitor concentration field
- $D_a, D_i$ = diffusion coefficients
- $r_a, r_i$ = reaction rates
- $\nabla^2$ = Laplacian operator (discrete: 5-point stencil)

### 2.3 Parameter Table

| Parameter | Symbol | Default | Units | Valid Range | Physical Meaning |
|-----------|--------|---------|-------|-------------|------------------|
| Activator diffusion | $D_a$ | 0.1 | (grid²/step) | [0.01, 0.25) | Short-range diffusion |
| Inhibitor diffusion | $D_i$ | 0.05 | (grid²/step) | [0.01, 0.25) | Long-range diffusion |
| Activator reaction rate | $r_a$ | 0.01 | 1/step | [0.001, 0.1] | Growth rate |
| Inhibitor reaction rate | $r_i$ | 0.02 | 1/step | [0.001, 0.1] | Damping rate |
| Turing threshold | $\theta$ | 0.75 | – | [0.5, 0.95] | Pattern activation threshold |
| Field diffusion | $\alpha$ | 0.18 | – | [0.05, 0.25) | Potential diffusion coefficient |
| Jitter variance | $\sigma^2$ | 0.0005 | – | [0, 0.01] | Stochastic noise strength |
| Grid size | $N$ | 64 | – | [4, 1024] | Spatial resolution |

**Biophysical Constraints (ENFORCED in code):**
- All diffusion coefficients < 0.25 for CFL stability
- Reaction rates ∈ [0.001, 0.1] for stable pattern dynamics
- Turing threshold ∈ [0.5, 0.95] for meaningful pattern activation
- Jitter variance ≤ 0.01 to prevent noise-induced instability

**Critical constraint for Turing instability (SIMPLIFICATION):**
For classical Turing patterns: $D_i > D_a$ (inhibitor must diffuse faster).
Our simplified model uses $D_i / D_a = 0.5$, which is tuned for visual patterns
rather than strict adherence to classical Turing instability conditions.

### 2.4 Discrete Laplacian (5-Point Stencil)

The continuous Laplacian is discretized on a 2D grid with periodic boundaries:

$$
\nabla^2 u_{i,j} \approx u_{i+1,j} + u_{i-1,j} + u_{i,j+1} + u_{i,j-1} - 4u_{i,j}
$$

### 2.5 Stability Criterion

For explicit Euler integration, the CFL-like stability condition is:

$$
\Delta t \cdot D \cdot \frac{4}{(\Delta x)^2} \leq 1
$$

With $\Delta x = 1$ (unit grid spacing) and $\Delta t = 1$ (per step):
- Maximum stable diffusion coefficient: $D_{\max} = 0.25$
- Our choice $D_a = 0.1$, $D_i = 0.05$, $\alpha = 0.18$ are all safely below this limit.

### 2.6 Membrane Potential Field Evolution

The main potential field $V(x, y, t)$ evolves via:

$$
V^{n+1}_{i,j} = V^n_{i,j} + \alpha \nabla^2 V^n_{i,j} + \text{growth events} + \text{Turing modulation}
$$

where:
- Initial condition: $V \sim \mathcal{N}(-70 \text{ mV}, 5 \text{ mV})$
- Growth events: Random spikes adding $\sim 20$ mV
- Turing modulation: $+5$ mV where $a > \theta$
- Clamping: $V \in [-95, 40]$ mV

### 2.7 Implementation Mapping

```
Code Location: src/mycelium_fractal_net/core/reaction_diffusion_engine.py

Classes:
- ReactionDiffusionConfig: Configuration with validated bounds
- ReactionDiffusionEngine: Simulation with stability checks
- ReactionDiffusionMetrics: Runtime statistics

Constants (with enforced bounds):
- DEFAULT_D_ACTIVATOR = 0.1    # D_a ∈ [0.01, 0.25)
- DEFAULT_D_INHIBITOR = 0.05   # D_i ∈ [0.01, 0.25)
- DEFAULT_R_ACTIVATOR = 0.01   # r_a ∈ [0.001, 0.1]
- DEFAULT_R_INHIBITOR = 0.02   # r_i ∈ [0.001, 0.1]
- DEFAULT_TURING_THRESHOLD = 0.75  # θ ∈ [0.5, 0.95]
- DEFAULT_FIELD_ALPHA = 0.18   # α ∈ [0.05, 0.25)
- FIELD_V_MIN = -0.095 V       # Field clamp lower bound
- FIELD_V_MAX = 0.040 V        # Field clamp upper bound
- MAX_STABLE_DIFFUSION = 0.25  # CFL limit

Discretization:
- Spatial: Uniform grid, periodic/Neumann/Dirichlet boundaries
- Temporal: Explicit Euler, dt = 1 step
```

### 2.8 Optional Stochastic Term (Quantum Jitter)

**SIMPLIFICATION:** The term "quantum jitter" is a **metaphor** for thermal/stochastic
fluctuations. No actual quantum effects are modeled.

For stochastic dynamics, Gaussian noise is added:

$$
V^{n+1} = V^n + \alpha \nabla^2 V^n + \xi
$$

where $\xi \sim \mathcal{N}(0, \sigma^2)$ with $\sigma^2 \in [0, 0.01]$ (default 0.0005).

### 2.9 Validation Invariants

These invariants are **tested and enforced** in `tests/core/test_reaction_diffusion_engine.py`:

1. **Boundedness**: $V \in [-95, 40]$ mV (enforced by clamping)
2. **Stability**: No NaN/Inf after 1000+ steps
3. **Activator/Inhibitor bounds**: $a, i \in [0, 1]$ (enforced by clamping)
4. **CFL compliance**: All D < 0.25 (checked at configuration time)
5. **Growth events**: With $p = 0.25$, expect ~25 events per 100 steps

---

## 3. Fractal Growth and Dimension Analysis

### 3.1 Physical Background

Mycelial networks exhibit fractal self-similarity across scales. The fractal dimension
quantifies how a pattern fills space:
- $D = 1$: Line (1D)
- $D = 2$: Filled plane (2D)
- $D \approx 1.6$: Typical mycelial network

### 3.2 Iterated Function System (IFS)

An IFS generates fractal patterns via repeated application of contractive affine
transformations. Each transformation has the form:

$$
\begin{pmatrix} x' \\ y' \end{pmatrix} = 
\begin{pmatrix} a & b \\ c & d \end{pmatrix}
\begin{pmatrix} x \\ y \end{pmatrix} +
\begin{pmatrix} e \\ f \end{pmatrix}
$$

**Contraction requirement**: $|ad - bc| < 1$ (ensures convergence)

**MFN Implementation:**
- Random rotation: $a = s\cos\theta$, $b = -s\sin\theta$, $c = s\sin\theta$, $d = s\cos\theta$
- Scale factor: $s \in [0.2, 0.5]$ (ensures contraction)
- Translation: $e, f \in [-1, 1]$

### 3.3 Lyapunov Exponent

The Lyapunov exponent $\lambda$ measures dynamical stability:

$$
\lambda = \lim_{n \to \infty} \frac{1}{n} \sum_{k=1}^{n} \ln|\det(J_k)|
$$

where $J_k$ is the Jacobian of the $k$-th transformation.

**Interpretation:**
- $\lambda < 0$: Stable (contractive) dynamics
- $\lambda > 0$: Unstable (expansive) dynamics

**Expected value for MFN IFS**: $\lambda \approx -2.1$ (stable)

### 3.4 Box-Counting Dimension

The fractal (box-counting) dimension $D$ is estimated by:

$$
D = \lim_{\epsilon \to 0} \frac{\ln N(\epsilon)}{\ln(1/\epsilon)}
$$

where $N(\epsilon)$ is the number of boxes of size $\epsilon$ needed to cover the pattern.

**Computational procedure:**
1. Threshold the field to create a binary pattern
2. For multiple scales $\epsilon_1, \epsilon_2, ..., \epsilon_k$, count occupied boxes $N(\epsilon_i)$
3. Fit linear regression: $\ln N(\epsilon) = D \cdot \ln(1/\epsilon) + c$
4. The slope $D$ is the fractal dimension

### 3.5 Parameter Table

| Parameter | Symbol | Default | Units | Valid Range | Physical Meaning |
|-----------|--------|---------|-------|-------------|------------------|
| IFS scale factor | $s$ | 0.2–0.5 | – | (0, 1) | Contraction strength |
| IFS rotation | $\theta$ | random | rad | [0, 2π] | Transformation angle |
| IFS translation | $e, f$ | ±1 | – | [-range, +range] | Pattern offset |
| Translation range | – | 1.0 | – | [0, 2] | Max translation magnitude |
| Number of transforms | $n_T$ | 4 | – | [2, 8] | Complexity of IFS |
| Number of points | $n_P$ | 10000 | – | [1000, 100000] | Resolution |
| Min box size | – | 2 | grid | ≥ 1 | Smallest scale |
| Max box size | – | N/2 | grid | ≤ N | Largest scale |
| Number of scales | – | 5 | – | [3, 10] | Log-regression points |

**Biophysical Constraints (ENFORCED in code):**
- Scale factors strictly < 1 for contraction (IFS stability)
- Number of transforms ∈ [2, 8] for meaningful patterns
- Number of points ∈ [1000, 100000] for fractal resolution
- Number of scales ∈ [3, 10] for reliable dimension regression

### 3.6 Expected Dimension Values

| Pattern Type | Expected $D$ | Reference |
|--------------|--------------|-----------|
| Sierpinski triangle | 1.585 | Exact |
| Cantor set | 0.631 | Exact |
| Mycelium (observed) | 1.4–1.9 | Empirical |
| MFN simulation | 1.4–1.9 | Validated |

**SIMPLIFICATION:** The "mycelium" dimension range [1.4, 1.9] is based on
analogy to biological mycelium, not direct measurement of the simulated patterns.

### 3.7 Implementation Mapping

```
Code Location: src/mycelium_fractal_net/core/fractal_growth_engine.py

Classes:
- FractalConfig: Configuration with validated bounds
- FractalGrowthEngine: IFS generation and dimension analysis
- FractalMetrics: Runtime statistics

Constants (with enforced bounds):
- NUM_POINTS_MIN = 1000, NUM_POINTS_MAX = 100000
- NUM_TRANSFORMS_MIN = 2, NUM_TRANSFORMS_MAX = 8
- SCALE_MIN_BOUND = 0.0 (exclusive), SCALE_MAX_BOUND = 1.0 (exclusive)
- TRANSLATION_RANGE_MAX = 2.0
- NUM_SCALES_MIN = 3, NUM_SCALES_MAX = 10
- LYAPUNOV_STABLE_MAX = 0.0

Functions:
- generate_ifs(num_points, num_transforms)
  Returns: (points, lyapunov_exponent)

- estimate_dimension(binary_field, min_box_size, max_box_size, num_scales)
  Returns: Estimated D

- compute_lyapunov_from_history(field_history, dt)
  Returns: Lyapunov exponent from time series

Algorithm:
- Box counting uses geometric scale spacing (np.geomspace)
- Linear regression via np.polyfit with R² quality metric
- Handles edge cases: uniform field → D = 0, empty field → D = 0
```

### 3.8 Validation Invariants

These invariants are **tested and enforced** in `tests/core/test_fractal_growth_engine.py`:

1. **Dimension bounds**: $0 \leq D \leq 2$ for 2D binary fields
2. **Lyapunov stability**: $\lambda < 0$ for contractive IFS (always enforced)
3. **Contraction requirement**: $|ad - bc| < 1$ for all transforms
4. **Point boundedness**: All IFS points finite (no divergence)
5. **Reproducibility**: Same seed → identical D

---

## 4. Numerical Implementation Notes

### 4.1 Discretization Summary

| Component | Spatial Discretization | Temporal Discretization | Stability Constraint |
|-----------|------------------------|-------------------------|----------------------|
| Laplacian diffusion | 5-point stencil | Explicit Euler | $D < 0.25$ |
| Turing reaction | Point-wise | Explicit Euler | $r \leq 0.1$ |
| IFS iteration | Random choice | – | $s < 1$ |
| Box-counting | Grid-based | – | min_size ≥ 1 |

### 4.2 Memory and Complexity

| Operation | Time Complexity | Space Complexity |
|-----------|-----------------|------------------|
| Nernst potential | $O(1)$ | $O(1)$ |
| Field simulation | $O(N^2 \cdot T)$ | $O(N^2)$ |
| Fractal IFS | $O(n_P)$ | $O(n_P)$ |
| Box-counting | $O(N^2 \cdot k)$ | $O(N^2)$ |

where $N$ = grid size, $T$ = steps, $n_P$ = points, $k$ = scales.

### 4.3 Clamping and Bounds

All computations enforce physical bounds:

| Quantity | Min | Max | Unit | Enforcement |
|----------|-----|-----|------|-------------|
| Ion concentration | $10^{-6}$ | – | M | `max(c, ION_CLAMP_MIN)` |
| Membrane potential | −95 | +40 | mV | `np.clip(field, -0.095, 0.040)` |
| Activator | 0 | 1 | – | `np.clip(activator, 0, 1)` |
| Inhibitor | 0 | 1 | – | `np.clip(inhibitor, 0, 1)` |
| IFS scale | 0.2 | 0.5 | – | `rng.uniform(0.2, 0.5)` |

---

## 5. References

### Classical Sources

1. **Nernst, W. (1889)**. "Die elektromotorische Wirksamkeit der Ionen."
   *Zeitschrift für Physikalische Chemie*, 4, 129–181.
   
2. **Turing, A.M. (1952)**. "The chemical basis of morphogenesis."
   *Philosophical Transactions of the Royal Society B*, 237, 37–72.
   
3. **Mandelbrot, B.B. (1982)**. *The Fractal Geometry of Nature*.
   W.H. Freeman and Company.

### Modern References

4. **Hille, B. (2001)**. *Ion Channels of Excitable Membranes*. 3rd ed.
   Sinauer Associates.
   
5. **Murray, J.D. (2003)**. *Mathematical Biology II: Spatial Models and
   Biomedical Applications*. 3rd ed. Springer.
   
6. **Cross, M.C. & Hohenberg, P.C. (1993)**. "Pattern formation outside
   of equilibrium." *Reviews of Modern Physics*, 65(3), 851–1112.

### Notes on References

- All references are to well-established textbooks and foundational papers
- No DOIs or specific page numbers are given to avoid potential errors
- For numerical methods, standard references include LeVeque (2007) for
  finite differences and Press et al. (2007) for general numerical recipes

---

## 6. Hypothesis vs. Established Theory

This section explicitly distinguishes between well-established physics/mathematics
and experimental/hypothetical aspects of the MFN model.

### Established (Textbook) Material

| Component | Status | Source |
|-----------|--------|--------|
| Nernst equation | **Established** | Electrochemistry, 1889+ |
| Turing patterns | **Established** | Mathematical biology, 1952+ |
| Box-counting dimension | **Established** | Fractal geometry, 1980s+ |
| Discrete Laplacian | **Established** | Numerical analysis |
| IFS fractals | **Established** | Chaos theory, 1980s+ |
| STDP learning rule | **Established** | Neurophysiology, Bi & Poo 1998 |
| Scaled dot-product attention | **Established** | Vaswani et al. 2017 |
| Krum aggregation | **Established** | Blanchard et al. 2017 |

### Experimental/Hypothetical Aspects

| Component | Status | Notes |
|-----------|--------|-------|
| Parameter values (D_a, D_i, r_a, r_i) | **Tuned** | Not derived from first principles; chosen for stability and pattern formation |
| Turing threshold = 0.75 | **Empirical** | Chosen for reasonable pattern activation |
| Mycelium fractal dimension range | **Hypothesis** | Based on analogy to biological mycelium, not direct measurement |
| "Quantum jitter" | **Metaphor** | Gaussian noise; not actual quantum effects |
| Coupling between Turing and potential field | **Design choice** | Not claimed to model real biology precisely |
| STDP parameter values (τ=20ms, A±) | **Tuned** | Based on Bi & Poo (1998) but simplified |
| Sparse attention topk=4 | **Empirical** | Chosen for efficiency vs. expressiveness tradeoff |
| Hierarchical Krum 70/30 weighting | **Design choice** | Balances Krum robustness with median stability |

---

## Appendix A: Sympy Verification

The Nernst equation can be symbolically verified:

```python
import sympy as sp

R, T, z, F, c_out, c_in = sp.symbols("R T z F c_out c_in", positive=True)
E_expr = (R * T) / (z * F) * sp.log(c_out / c_in)

# Substitute K+ values at 37°C
subs = {
    R: 8.314,       # J/(mol·K)
    T: 310,         # K
    z: 1,           # K+ valence
    F: 96485.33,    # C/mol
    c_out: 5e-3,    # 5 mM
    c_in: 140e-3,   # 140 mM
}

E_K = float(E_expr.subs(subs).evalf())
print(f"E_K = {E_K * 1000:.2f} mV")  # Expected: -89 mV
```

---

## Appendix B: Stability Analysis

### B.1 Diffusion Stability

For 2D diffusion with explicit Euler:

$$
u^{n+1}_{i,j} = u^n_{i,j} + \alpha \nabla^2 u^n_{i,j}
$$

The von Neumann stability analysis gives the constraint:

$$
\alpha \leq \frac{1}{4}
$$

With $\alpha = 0.18$, we are within the stable regime.

### B.2 Turing Instability Condition

Pattern formation requires the system to be:
- Stable in the absence of diffusion
- Unstable with diffusion

This occurs when:
- $D_i / D_a > \text{some threshold}$ (typically > 1)
- Reaction rates satisfy specific inequalities

Our parameters ($D_i / D_a = 0.5$, $r_i / r_a = 2$) are tuned for
pattern formation without numerical instability.

---

## Appendix C: STDP Mathematical Model

### C.1 Physical Background

Spike-Timing Dependent Plasticity (STDP) is a biological learning rule discovered
in hippocampal neurons (Bi & Poo, 1998). Weight changes depend on relative spike
timing between pre- and postsynaptic neurons.

### C.2 Governing Equations

The STDP weight update rule:

$$
\Delta w = \begin{cases}
A_+ e^{-\Delta t / \tau_+} & \text{if } \Delta t > 0 \text{ (LTP)} \\
-A_- e^{\Delta t / \tau_-} & \text{if } \Delta t < 0 \text{ (LTD)}
\end{cases}
$$

where:
- $\Delta t = t_{\text{post}} - t_{\text{pre}}$ (spike timing difference)
- $\tau_+, \tau_-$ = time constants
- $A_+, A_-$ = learning rate magnitudes

### C.3 Parameter Table

| Parameter | Symbol | Value | Units | Valid Range | Physical Meaning |
|-----------|--------|-------|-------|-------------|------------------|
| LTP time constant | $\tau_+$ | 20 | ms | 5–100 | NMDA receptor decay |
| LTD time constant | $\tau_-$ | 20 | ms | 5–100 | Calcium decay time |
| LTP magnitude | $A_+$ | 0.01 | – | 0.001–0.1 | Potentiation strength |
| LTD magnitude | $A_-$ | 0.012 | – | 0.001–0.1 | Depression strength |
| **Asymmetry ratio** | $A_-/A_+$ | 1.2 | – | > 1 | Network stability |

### C.4 Stability Constraint

The asymmetry $A_- > A_+$ is critical for network stability:
- Prevents runaway LTP (unbounded weight growth)
- Ensures homeostatic equilibrium
- Empirically observed ratio: 1.0–1.5 (Bi & Poo, 1998)

### C.5 Numerical Stability

For large $|\Delta t|$, exponential terms can underflow/overflow.
Implementation uses clamped exponential arguments with `EXP_CLAMP_MAX = 50`:

$$
\text{exp\_arg} = \text{clamp}(-\Delta t / \tau, -\text{EXP\_CLAMP\_MAX}, +\text{EXP\_CLAMP\_MAX})
$$

This ensures $e^{-50} \approx 10^{-22}$ (effectively zero) without NaN issues.

---

## Appendix D: Sparse Attention Mathematical Model

### D.1 Standard Attention

Scaled dot-product attention (Vaswani et al., 2017):

$$
\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

where:
- $Q, K, V$ = query, key, value matrices
- $d_k$ = key dimension
- $\sqrt{d_k}$ = scaling factor

### D.2 Scaling Factor Justification

For random $Q, K$ with unit variance:
$$
\text{Var}(Q \cdot K) = d_k
$$

Without scaling, large $d_k$ causes softmax saturation. Division by $\sqrt{d_k}$
normalizes variance to 1, ensuring gradient flow.

### D.3 Sparse Top-K Selection

For each query position $i$, retain only top-$k$ attention scores:

$$
\text{SparseAttn}_i = \text{softmax}(\text{top}_k(s_i))V
$$

where $s_i = Q_i K^T / \sqrt{d_k}$ are the attention scores for query $i$.

### D.4 Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| Standard attention | $O(n^2 d)$ | $O(n^2)$ |
| Sparse attention (top-k) | $O(n \cdot k \cdot d)$ | $O(n \cdot k)$ |

Speedup factor: $n/k$ (e.g., 8× for $n=32$, $k=4$)

### D.5 Parameter Constraints

| Parameter | Valid Range | Default | Notes |
|-----------|-------------|---------|-------|
| $k$ (topk) | $[1, n]$ | 4 | At least 1 for valid softmax |
| $d_k$ (embed_dim) | $> 0$ | – | Must be positive |

---

## Appendix E: Byzantine-Robust Aggregation

### E.1 Krum Algorithm (Blanchard et al., 2017)

For $n$ gradients $g_1, \ldots, g_n$ with $f$ Byzantine (adversarial) gradients,
Krum selects the gradient closest to the majority:

$$
\text{Krum}(g_1, \ldots, g_n) = g_i \text{ where } i = \arg\min_j s(g_j)
$$

$$
s(g_j) = \sum_{k \in N_j} \|g_j - g_k\|^2
$$

where $N_j$ is the set of $(n - f - 2)$ nearest neighbors of $g_j$.

### E.2 Byzantine Tolerance Guarantee

Krum provides convergence guarantees when:

$$
f < \frac{n - 2}{2}
$$

This means for $n$ clients, at most $\lfloor(n-2)/2\rfloor$ can be Byzantine.

| Clients $n$ | Max Byzantine $f$ |
|-------------|-------------------|
| 4 | 0 |
| 5 | 1 |
| 6 | 1 |
| 10 | 3 |
| 100 | 48 |

### E.3 Hierarchical Extension

Two-level aggregation for scalability:

1. **Level 1 (Cluster):** Apply Krum within each of $C$ clusters
   $$
   g_c^{(1)} = \text{Krum}(\{g_i : i \in \text{cluster}_c\})
   $$

2. **Level 2 (Global):** Combine cluster representatives
   $$
   g^* = 0.7 \cdot \text{Krum}(g_1^{(1)}, \ldots, g_C^{(1)}) + 0.3 \cdot \text{Median}(g_1^{(1)}, \ldots, g_C^{(1)})
   $$

The median component provides additional robustness against coordinate-wise attacks.

### E.4 Complexity Analysis

| Configuration | Time Complexity |
|---------------|-----------------|
| Single Krum | $O(n^2 \cdot d)$ |
| Hierarchical ($C$ clusters) | $O(n^2/C \cdot d + C^2 \cdot d)$ |
| Optimal $C$ | $\approx n^{2/3}$ |

### E.5 Parameter Table

| Parameter | Symbol | Default | Valid Range | Notes |
|-----------|--------|---------|-------------|-------|
| Clusters | $C$ | 100 | $[1, n]$ | Number of aggregation groups |
| Byzantine fraction | $f_{\text{frac}}$ | 0.2 | $[0, 0.5)$ | Must be < 50% |
| Sample fraction | – | 0.1 | $(0, 1]$ | For large $n > 1000$ |

---

*Document Version: 1.1*
*Last Updated: 2025*
*Applies to: MyceliumFractalNet v4.1.0*
