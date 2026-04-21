# ARCHIVED · manuscript/arxiv_submission.tex §2 "Theoretical Framework" (pre-canon-closure)

> **Status.** Archived 2026-04-21. Superseded by
> `manuscript/arxiv_submission.tex` §2 "Analytical result for Kuramoto"
> (canon closure v1.0) and by `docs/CLAIM_BOUNDARY.md` §CLAIM ROWS
> (C-001..C-004).
>
> **Why archived.** The prior §2 conflated the Kuramoto analytical
> anchor with multiple substrate-level empirical frameworks
> (branching process, BTW sandpile, directed percolation, information-
> theoretic complexity, cross-substrate hypothesis H1/H2). Under canon
> closure, §2 is reserved for the **proved** layer (Kuramoto dense-
> graph Lemma 1). Cross-substrate material belongs in §3 (Methods)
> and §4 (Results), already present in the manuscript.
>
> **Retention policy.** This file is retained for historical context
> and for re-use of individual fragments (e.g. branching-process and
> SOC citations) in follow-up methodological extensions. It is not
> active canon and must not be cited as if it were.

---

## Archived content (verbatim extraction from
## `manuscript/arxiv_submission.tex` at SHA `1f9e9fe4`, lines 113–196)

```latex
% ====================================================================
\section{Theoretical Framework}

\subsection{Scaling relation}

For a system with topological complexity $C$ (measuring information richness, structural diversity, or phase-space dimensionality) and thermodynamic cost $K$ (measuring energy expenditure, computational effort, or dissipation per unit complexity), we define the gamma-scaling relation:
\begin{equation}
K = A \cdot C^{-\gamma}
\end{equation}

Taking logarithms:
\begin{equation}
\log K = -\gamma \log C + \log A
\end{equation}

The exponent $\gamma$ characterizes the system's efficiency-complexity tradeoff:
\begin{itemize}
\item $\gamma > 1$: \emph{over-determined} --- cost decreases faster than complexity increases (convergent regime)
\item $\gamma < 1$: \emph{under-determined} --- cost decreases slower than complexity increases (divergent regime)
\item $\gamma = 1$: \emph{critical balance} --- cost and complexity scale inversely at unit rate (metastable regime)
\end{itemize}

\subsection{Connection to criticality diagnostics}

The gamma-scaling exponent relates to established criticality measures:
\begin{itemize}
\item \textbf{Branching ratio} $\sigma$: In spiking networks, $\sigma \approx 1.0$ indicates criticality~\cite{beggs2003}. Our BN-Syn substrate measures $\gamma = 0.950$ when $\sigma$ is tuned to the critical regime.
\item \textbf{Kuramoto order parameter} $r$: In coupled oscillator systems, coherence $r \in [0,1]$ measures synchronization. Our market substrate computes $\gamma$ from Kuramoto coherence trajectories, yielding $\gamma = 1.081$.\footnote{$\gamma = 1.081$ refers to the market Kuramoto substrate (financial coherence trajectories, illustrative). $\gamma = 0.980$ in Table~1 refers to simulated Kuramoto oscillators at critical coupling $K_c$. These are distinct substrates.}
\item \textbf{Spectral radius} $\rho$: The largest eigenvalue of the system's Jacobian. In the neosynaptex cross-domain integrator, $\rho \approx 1.0$ and $\gamma \approx 1.0$ co-occur in the METASTABLE phase.
\end{itemize}

\subsection{Information-theoretic complexity}

For the human--AI cognitive substrate, we define complexity using Shannon information theory:
\begin{equation}
C = H(W) \cdot \log(1 + |V|) \cdot \text{TTR}
\end{equation}
where $H(W) = -\sum_i p_i \log_2 p_i$ is the Shannon entropy of the word frequency distribution, $|V|$ is the vocabulary size (unique words), and $\text{TTR} = |V|/|W|$ is the type-token ratio. The thermodynamic cost is:
\begin{equation}
K = \frac{|W|}{C}
\end{equation}
measuring total words (effort) per unit of information complexity.

\subsection{Hypotheses}

\subsubsection{Hypothesis H1: Intelligence as a Dynamical Regime}

\textbf{Statement:} Truth is not inevitable --- it is the result of independent verification between autonomous witnesses. Within the framework of H1, intelligence is defined as a dynamical regime verified through synchronous phase shifts ($\gamma$) across independent channels of a single substrate, with coherent recovery.

\textbf{Formalization:}
\begin{equation}
\forall\, S_i \in \{\text{substrates at metastability}\}:\; \gamma_{S_i} \in [0.85, 1.15]
\end{equation}
with 95\% CI containing $1.0$.

\textbf{Verification criterion:} H1 is supported if $\gamma \in [0.85, 1.15]$ with 95\% CI containing 1.0 across $N \geq 3$ independent substrates from distinct physical domains, each passing surrogate testing ($p < 0.05$).

\textbf{Status: SUPPORTED} --- three independent biological substrates (zebrafish, HRV PhysioNet, EEG PhysioNet), cross-substrate CI from Tier~1 contains unity. All Tier~1 IAAFT $p$-values $< 0.05$. BN-Syn finite-size deviation ($\gamma \approx 0.49$) confirms methodology is not trivially producing $\gamma \approx 1.0$.

\subsubsection{Hypothesis H2: Computational Efficiency Is a Regime Property}

\textbf{Statement:} The regime $\gamma \approx 1$ corresponds to a state that maximizes computational capacity at minimal cost of plasticity maintenance. This is an open claim requiring separate experimental and theoretical verification.

\textbf{Energy-Regime Conjecture} ($\mathcal{C}_E$):
\begin{equation}
\mathcal{C}_E:\quad \gamma \approx 1 \Longleftrightarrow \text{local min of dissipation preserving plasticity}
\end{equation}

\textbf{Status of $\mathcal{C}_E$: CONJECTURE} --- not theorem, not derivation. Qualitative argument only. Formal derivation of the $\beta \to \varepsilon$ bridge is open work.

\subsection{Theoretical basis: $\gamma = 1.0$ in mean-field criticality}

The result $\gamma = 1.0$ follows from mean-field theory of critical phenomena in multiple universality classes.

\textbf{Branching process at $\sigma = 1$.} In a critical branching process, each event generates on average $\sigma = 1$ successor. The cost of propagating one unit of topological information is exactly one unit of energy~\cite{harris1963}. This gives $K = C^{-1}$ directly, yielding $\gamma = 1$.

\textbf{Self-organized criticality.} In the mean-field BTW sandpile~\cite{bak1987}, avalanche size $S$ and duration $T$ satisfy $\langle S \rangle \sim T^{d_f/d}$. In mean-field ($d \geq d_c$), $d_f = d$, giving $\langle S \rangle \sim T^1$. The cost-complexity ratio $K/C \sim S/T = \text{const}$, yielding $\gamma = 1$.

\textbf{Directed percolation universality.} Neural criticality belongs to the directed percolation universality class~\cite{munoz1999,beggs2003}. In mean-field DP, the branching ratio $\sigma = 1$ at the critical point, and $\tau = 3/2$ (avalanche size exponent). The scaling relation $\gamma = (\tau_T - 1)/(\tau_S - 1)$ evaluates to exactly $1.0$ in mean field.

\textbf{Finite-size corrections.} Below the upper critical dimension $d_c$, corrections of order $\varepsilon = d_c - d$ appear, pushing $\gamma$ away from $1.0$. Our BN-Syn simulation ($N\!=\!200$ neurons, $k\!=\!10$ sparse connectivity) yields $\gamma \approx 0.49$, consistent with finite-size deviations from the mean-field prediction.

\textbf{Spectral connection.} At SOC, the power spectral density follows $S(f) \sim f^{-\beta}$ with $\beta = 1$ ($1/f$ noise)~\cite{bak1987}. The spectral exponent $\beta$ is related to the Hurst exponent $H$ via $\beta = 2H + 1$ (for fractional Brownian motion), giving $H = 0$ at criticality. In the HRV VLF range and EEG aperiodic component, $\beta \approx 1.0$ during healthy/active states corresponds to $\gamma_{\text{PSD}} \approx 1.0$, consistent with the topo-cost framework.

% ====================================================================
```

---

**claim_status:** archived · pre-canon-closure
**archived_at:** 2026-04-21
**supersedes:** n/a
**superseded_by:** `manuscript/arxiv_submission.tex` §2 (canon-closure v1.0)
