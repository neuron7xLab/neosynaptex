# Lemma 1 · Kuramoto γ = 1 unity

> **Role.** Operational working document for Claim C-001
> (`docs/CLAIM_BOUNDARY.md` §CLAIM ROWS).
> The manuscript's `§2 Analytical result for Kuramoto` is the
> publication-quality condensation; this document is the verbose
> internal record that unpacks RoH assumptions, normalization
> conventions, finite-size behaviour, and open problems.
>
> **Referenced from.**
> - `docs/CLAIM_BOUNDARY.md` C-001 Evidence
> - `docs/REVIEWER_ATTACK_SURFACE.md` rows 1, 2, 5, 6, 7
> - `docs/CONTRIBUTION_STATEMENT.md` pillar 2
> - `manuscript/arxiv_submission.tex` §2 (cross-reference to this doc)
>
> **Evidence file.** `evidence/lemma_1_numerical.json`.
> **Verification script.**
> `experiments/lemma_1_verification/verify_kuramoto_gamma_unity.py`.
> **Ledger entry.** `evidence/gamma_ledger.json#lemma_1_kuramoto_dense`.

---

## 1. Statement

Let $G_N = K_N$ be the complete graph on $N$ vertices, with adjacency
matrix $A_N$. Consider the Kuramoto model

$$
\dot{\theta}_i \;=\; \omega_i \;+\; K \!\!\sum_{j : A_{ij}=1}\! \sin(\theta_j - \theta_i),
\qquad i = 1, \dots, N,
$$

with natural frequencies $\omega_i$ drawn i.i.d. from a unimodal
density $g$ and coupling strength $K$ applied to the *unnormalized*
adjacency. Define the operational cost–complexity pair

$$
K := J_c \;\text{(critical coupling)},
\qquad
C := \lambda_1(A_N) \;\text{(largest adjacency eigenvalue)}.
$$

**Lemma 1 (γ-unity for Kuramoto on dense symmetric graphs).**
Under assumptions (A0)–(A3) below,

$$
K(C) \;\sim\; \kappa_0 \cdot C^{-1},\qquad\text{i.e.}\qquad \gamma \;=\; 1,
\quad \text{with}\quad \kappa_0 \;=\; \frac{2}{\pi\,g(0)}.
$$

For the canonical special case $g(\omega) = \Delta/(\pi(\omega^2+\Delta^2))$
(Lorentzian/Cauchy, scale $\Delta$), $\kappa_0 = 2\Delta$.

---

## 2. Assumptions (A0)–(A3)

| Tag  | Assumption |
|------|------------|
| (A0) | Graph sequence $\{G_N\}$ is symmetric and strongly connected. |
| (A1) | Graph is dense: $|E(G_N)| = \Theta(N^2)$. For $G_N = K_N$ this is exact ($|E| = N(N-1)/2$). |
| (A2) | The spectral radius $\lambda_1(A_N) \to \infty$ as $N \to \infty$, with $\lambda_1(A_N)/N \to c > 0$ (mean-field regime). For $K_N$: $\lambda_1 = N-1$, $c = 1$. |
| (A3) | The natural-frequency density $g$ is unimodal, $C^2$, symmetric about its mode (WLOG $g(0) = \max g$), and either has bounded support or sub-exponential tails. |

Assumption (A2) is what makes Lemma 1 a lemma **about the Kuramoto
dense-graph regime**. It rules out sparse graphs (Erdős–Rényi with
$p_N \to 0$), expanders of sub-linear degree, and any topology whose
largest eigenvalue grows sublinearly in $N$. Those regimes are
explicitly open problems; see §7.

---

## 3. Proof sketch (Restrepo–Ott–Hunt 2005)

Restrepo, Ott & Hunt (*Phys. Rev. E* 71, 036151, 2005) derive the
onset of coherence on a general symmetric graph via the linearization
around $\theta_i \equiv$ const:

$$
K_c \;=\; \frac{2}{\pi\,g(0)} \cdot \frac{1}{\lambda_1(A_N)}.
$$

This is the RoH spectral onset formula. Substituting the operational
definitions,

$$
J_c \;=\; \frac{\kappa_0}{\lambda_1(A_N)}
\;=\; \kappa_0 \cdot C^{-1},
\qquad \kappa_0 = \frac{2}{\pi\,g(0)}.
$$

Taking logarithms gives $\log J_c = \log \kappa_0 - \log C$, i.e.
$K(C) \sim \kappa_0 \cdot C^{-\gamma}$ with $\gamma = 1$ exactly.
Validity of the linearization step rests on (A0)–(A3):
(A0)–(A2) supply a well-defined $\lambda_1$ with an $O(N)$-sized
spectral gap; (A3) makes the self-consistency equation
$r = \int g(\omega)\,\chi(\omega, K, r)\,d\omega$ regular at $r \to 0^+$.

The proof is a **reformulation**, not a rederivation. The contribution
here is operational: (a) the reframing of critical onset as a
*cost-complexity law* $K(C)$, (b) the explicit identification of the
analytical anchor $\gamma = 1$, and (c) the numerical verification
under explicit assumption audit (see §6).

---

## 4. Normalization-convention analysis

The Kuramoto equation can be written in two operationally distinct
but physically equivalent forms:

**(i) Unnormalized-sum convention (Lemma 1's convention).**

$$
\dot\theta_i = \omega_i + K_\mathrm{sum} \!\!\sum_{j} A_{ij}\sin(\theta_j-\theta_i).
$$

Here $K_\mathrm{sum}$ is the coupling *per edge*. For $G = K_N$ the
vertex has degree $N-1$, so the effective mean-field coupling is
$(N-1)\,K_\mathrm{sum}$. The RoH onset $K_c = \kappa_0/\lambda_1$
gives $K_\mathrm{sum}^{(c)} = \kappa_0/(N-1)$. This is the
convention that makes $\gamma = 1$ exact on $K_N$ via
$\lambda_1 = N-1$.

**(ii) Mean-field-normalized convention.**

$$
\dot\theta_i = \omega_i + \frac{K_\mathrm{mf}}{N}\sum_{j} \sin(\theta_j-\theta_i).
$$

On $K_N$ this is what Kuramoto 1975 actually wrote, and the onset is
$K_\mathrm{mf}^{(c)} = \kappa_0 = 2\Delta$ for Lorentzian $g$ —
independent of $N$. Converting between conventions on $K_N$:
$K_\mathrm{sum} = K_\mathrm{mf}/(N-1)$ (equivalent because every
neighbour is connected).

**Adapter convention in this repo.** The `substrates/kuramoto/`
adapter writes the mean-field form (ii). The lemma is stated in
form (i) because only (i) makes $C = \lambda_1(A)$ a *graph-intrinsic*
complexity — it does not carry a hidden $1/N$ factor.
The verification script simulates (ii) and converts: it measures
$K_\mathrm{mf}^{(c)}$ and reports $K_\mathrm{sum}^{(c)} =
K_\mathrm{mf}^{(c)}/(N-1)$ in the log-log fit.

**Why the adapter keeps (ii).** Convention (ii) is the Kuramoto-1975
textbook form and is the one every existing cross-substrate tool
assumes. Rewriting the adapter to (i) would cascade into every
substrate workflow without changing any physics. The lemma's bridge
between conventions is documented in manuscript §2.6.

---

## 5. Special case $\Delta = 0.5$

For the Lorentzian $g(\omega) = \Delta/(\pi(\omega^2 + \Delta^2))$,

$$
g(0) \;=\; \frac{1}{\pi\Delta},
\qquad
\kappa_0 \;=\; \frac{2}{\pi\,g(0)} \;=\; 2\Delta.
$$

For the canonical choice $\Delta = 0.5$: $\kappa_0 = 1$. Hence the
Lemma 1 prediction on $K_N$ is

$$
K_\mathrm{sum}^{(c)}(N) \;=\; \frac{1}{N-1},
\qquad
K_\mathrm{mf}^{(c)}(N) \;=\; 1 \;\text{(constant in $N$).}
$$

These are the two reference curves the verification script checks
against (dashed line in `manuscript/figures/lemma_1_verification.pdf`).

---

## 6. Numerical verification summary

Driver: `experiments/lemma_1_verification/verify_kuramoto_gamma_unity.py`
Seed: master = 7.
Parameters: $N \in \{30, 100, 300, 1000, 3000\}$, 48 samples per $N$,
Lorentzian $\Delta = 0.5$, integration with Heun's method, $dt = 0.1$,
total time $T = 120$.

**K_c estimator.** For each sample, simulate at a grid of
supercritical couplings $K \in \{1.1, 1.2, \dots, 2.0\}$ (mid-
supercritical, chosen to minimise both near-critical noise and $r\to1$
saturation bias). Collect time-averaged $r$ over the second half of
each trajectory. Filter to samples with $r \in [0.3, 0.999)$. For each
qualifying sample use the Kuramoto mean-field self-consistency
identity $r^2 = (K - K_c)/K$ to infer $K_c = K(1 - r^2)$ and take the
median across the grid.

**Fit.** OLS on $\log K_\mathrm{sum}^{(c)} = \log A - \gamma \log(N-1)$.
Bootstrap CI with 2 000 resamples.

**Primary result (full fit, $N \in \{30, 100, 300, 1000, 3000\}$):**

$$
\hat\gamma \;=\; 0.9923,
\qquad
\text{95\% CI} \;=\; [0.9811,\; 1.0032],
\qquad
\hat A \;=\; 0.9428.
$$

The 95% CI on $\hat\gamma$ contains the analytical value $1.0$; the
point estimate on $\hat A$ sits 6% below the theoretical $\kappa_0 = 1$,
consistent with the finite-size bias documented in §7.

**Secondary result (asymptotic fit, $N \geq 100$):**
$\hat\gamma = 0.9875$, CI $= [0.9754,\; 0.9995]$. The CI misses 1.0
by $5 \times 10^{-4}$ — not an analytical falsification but a
systematic finite-size drift discussed next.

The operator directive 2026-04-21 elected the **full fit** as the
primary anchor, recorded in `evidence/lemma_1_numerical.json`
under the `primary_fit` key with
`anchor_value_for_abstract = 0.9923`.

---

## 7. Open issues

### 7.1 Pre-asymptotic bias in the mean-field self-consistency estimator

For finite $N$, the identity $r^2 = (K - K_c)/K$ carries $O(1/N)$
corrections from the Kuramoto 1975 derivation. These corrections
manifest as a mild monotonic drift of the estimated $K_\mathrm{mf}^{(c)}$
from $\approx 0.95$ at $N = 30$ to $\approx 1.00$ at $N = 3000$. The
drift pulls the asymptotic slope estimate to
$\hat\gamma_\mathrm{asym} \approx 0.987$ — within $1.3\%$ of the
analytical value, but with a tight enough CI to formally exclude
$1.0$. The full fit neutralises the drift because the $N = 30$
point's low $K$ combines with the extended $\log(N-1)$ range to
restore a slope of $-1$ within noise.

Alternative K_c estimators tested (threshold crossing at $r = 0.3$,
wider K_grid including near-critical and saturation regimes) all show
the same sign of bias, confirming it is a property of the finite-$N$
mean-field approximation, not a methodological artefact of the
estimator choice.

A cleaner future resolution would be: fit the full finite-size scaling
form $r(K, N) = r_0((K-K_c) N^{1/2})$ instead of the leading-order
mean-field identity, and extract $K_c$ by Nelder–Mead on the
combined $(K, N)$ surface. That is deferred to a follow-up and
does not affect Lemma 1 as an analytical statement.

### 7.2 Non-complete graphs

All numerical verification above is on $K_N$. Assumptions (A1)–(A3)
are trivially satisfied there. Non-trivial spectral cases remain
open:

- **Erdős–Rényi $G(N, p)$, $p$ fixed as $N \to \infty$.** (A2) holds
  with $\lambda_1 \approx Np$. Simulation is straightforward; the
  question is whether the $K(C) \sim C^{-1}$ relation survives the
  non-regular degree distribution.
- **Sparse expanders (e.g. random $d$-regular, $d$ fixed).** (A1)
  *fails*: $|E| = \Theta(N)$, not $\Theta(N^2)$. Lemma 1 as stated
  does not apply. The RoH formula is still valid but the cost–complexity
  relation takes a different form.
- **Small-world / Watts–Strogatz.** Spectral structure is non-trivial
  and the mean-field derivation needs rethinking.

### 7.3 Non-Lorentzian frequency distributions

Assumption (A3) permits any unimodal $C^2$ density with bounded support
or sub-exponential tails. Different densities change $\kappa_0 = 2/(\pi\,g(0))$
but **not** $\gamma$. A sanity-check run with Gaussian $\omega_i$
would verify that $\hat\gamma \approx 1$ with a different $\hat A$ —
a follow-up item, not a gap in the lemma.

### 7.4 Stochastic Kuramoto (noisy dynamics)

The deterministic model above has no additive noise on
$\dot\theta_i$. Noise shifts $g$ (convolves with the diffusion kernel)
and renormalises $\kappa_0$. $\gamma = 1$ is expected to survive
but requires the noisy-Kuramoto analogue of the RoH derivation.

---

## 8. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-21 | Initial canon-closure version. Primary anchor $\hat\gamma = 0.9923$ per operator directive. |

---

*⊛ Claim C-001 operational record · canon-closure v1.0 · 2026-04-21*
