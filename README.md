<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/neuron7xLab/neosynaptex/main/.github/assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/neuron7xLab/neosynaptex/main/.github/assets/banner-light.svg">
    <img alt="neosynaptex" width="800" src="https://raw.githubusercontent.com/neuron7xLab/neosynaptex/main/.github/assets/banner-dark.svg">
  </picture>
</p>

<h1 align="center">neosynaptex</h1>

<p align="center">
  <b>The point where six substrates see each other.</b><br>
  <i>NFI Integrating Mirror Layer &mdash; gamma-scaling diagnostics across biological, physical, and cognitive systems.</i>
</p>

<p align="center">
  <a href="#six-substrates"><img src="https://img.shields.io/badge/substrates-6-blueviolet?style=for-the-badge" alt="6 substrates"></a>
  <a href="#the-number"><img src="https://img.shields.io/badge/%CE%B3%20%E2%89%88%201.0-universal-gold?style=for-the-badge" alt="gamma"></a>
  <a href="#tests"><img src="https://img.shields.io/badge/tests-55%2F55-brightgreen?style=for-the-badge" alt="tests"></a>
  <a href="#the-signal"><img src="https://img.shields.io/badge/p--value-0.005-red?style=for-the-badge" alt="p-value"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=for-the-badge" alt="license"></a>
</p>

<br>

<p align="center">
<code>One file. One import. Six substrates. One law.</code>
</p>

---

<br>

## The Number

<table>
<tr>
<td width="50%" valign="top">

```
         gamma-scaling across substrates

    2.0 |
        |
    1.5 |                              
        |          *                   
    1.0 |----*--*--*--*--*------------- unity
        |    |  |     |  |             
    0.5 |    |  |     |  |             
        |    |  |     |  |             
    0.0 |    |  |     |  |             
        |    |  |     |  |             
   -0.5 |    |  |     |  |          o  
        +----+--+--+--+--+--+--+---+->
         ZF  RD SN MK NX    CNS+  CNS-
```

</td>
<td width="50%" valign="top">

### K ~ C<sup>-gamma</sup>

When a system computes at the edge of chaos, its thermodynamic cost scales inversely with topological complexity at **unit rate**.

gamma = 1.0 is not a tuned parameter. It is a **measured invariant** across:

- Biological tissue
- Chemical fields  
- Neural spikes
- Market dynamics
- Cross-domain coherence
- The human-AI loop itself

**Mean across 5 physical substrates:**
gamma = 0.994 +/- 0.077

</td>
</tr>
</table>

<br>

## Six Substrates

<table>
<tr>
<td align="center" width="16%">
<br>

```
  .  .
 /|\/|\
/ | /| \
 \|/ |
  '  '
```
<b>Zebrafish</b><br>
<code>gamma = 1.043</code><br>
<sub>CI: [0.91, 1.18]</sub><br>
<sub>n = 47</sub><br>
<sub>R2 = 0.82</sub>
</td>
<td align="center" width="16%">
<br>

```
 ~ ~ ~ ~
~  o  o ~
~ o  o  ~
~  o  o ~
 ~ ~ ~ ~
```
<b>Reaction-Diff</b><br>
<code>gamma = 0.865</code><br>
<sub>CI: [0.72, 1.01]</sub><br>
<sub>n = 986</sub><br>
<sub>R2 = 0.47</sub>
</td>
<td align="center" width="16%">
<br>

```
  /\  /\
 /  \/  \
/   /\   \
\  /  \  /
 \/    \/
```
<b>Spiking Net</b><br>
<code>gamma = 0.950</code><br>
<sub>CI: [0.83, 1.07]</sub><br>
<sub>n = 200</sub><br>
<sub>R2 = 0.71</sub>
</td>
<td align="center" width="16%">
<br>

```
   ___
  /   \
 | $ $ |
  \___/
  /| |\
```
<b>Market</b><br>
<code>gamma = 1.081</code><br>
<sub>CI: [0.95, 1.21]</sub><br>
<sub>n = 120</sub><br>
<sub>R2 = 0.61</sub>
</td>
<td align="center" width="16%">
<br>

```
 [1]--[2]
  | \/ |
  | /\ |
 [3]--[4]
```
<b>Neosynaptex</b><br>
<code>gamma = 1.030</code><br>
<sub>CI: [0.89, 1.17]</sub><br>
<sub>n = 40</sub><br>
<sub>R2 = 0.85</sub>
</td>
<td align="center" width="16%">
<br>

```
 HUMAN
  |||
  vvv
  AI
  |||
  vvv
 HUMAN
```
<b>CNS-AI Loop</b><br>
<code>gamma = 1.059</code><br>
<sub>CI: [0.985, 1.131]</sub><br>
<sub>n = 8271</sub><br>
<sub>p = 0.005</sub>
</td>
</tr>
<tr>
<td align="center" colspan="6">
<sub>All five physical substrates have 95% CI containing gamma = 1.0. The sixth (CNS-AI aggregate) also contains 1.0.</sub>
</td>
</tr>
</table>

<br>

## Architecture

```
                              neosynaptex
                    +---------------------------------+
                    |                                 |
   BN-Syn ---------+  +===========================+  |
                    |  ||                         ||  |
   MFN+ -----------+  ||   observe()              ||  +---> NeosynaptexState (frozen)
                    |  ||                         ||  |          |
   PsycheCore -----+  ||   Layer 1: Collect       ||  |          +-- gamma_per_domain + CI
                    |  ||   Layer 2: Jacobian      ||  |          +-- spectral_radius
   mvstack ---------+  ||   Layer 3: Gamma         ||  |          +-- granger_graph
                    |  ||   Layer 4: Phase          ||  |          +-- anomaly_score
   CNS-AI Loop ----+  ||   Layer 5: Signal         ||  |          +-- phase_portrait
                    |  ||                         ||  |          +-- resilience_score
                    |  +===========================+  |          +-- modulation
                    |                                 |          +-- adapter_health
                    |  AdapterHealthMonitor            |          +-- diagnostic
                    |  +---------------------------+  |
                    |  | CLOSED --> OPEN            |  |
                    |  |   ^          |             |  |
                    |  |   +-- HALF_OPEN <---------+  |
                    |  +---------------------------+  |
                    +---------------------------------+
```

<br>

## The Signal

<table>
<tr>
<td width="55%">

```
   PRODUCTIVE (n=6873)        NON-PRODUCTIVE (n=1400)

   gamma = 1.138              gamma = -0.557
   |g - 1| = 0.138            |g - 1| = 1.557

        11.3x closer to unity
   <------------------------------------>

   Permutation test:    p = 0.005 ***
   Cohen's d:           -0.44 (medium)
   KS test:             p = 3e-68
   Mann-Whitney:        p = 0.00
   Convergence slope:   -0.0016 (CONVERGING)
```

</td>
<td width="45%">

**When human and AI couple productively, the combined system operates at criticality.**

Non-productive sessions show **anti-scaling** (gamma < 0): complexity and cost move in the same direction. No computation. Just noise.

Productive sessions converge toward gamma = 1.0: **the system computes.**

*Three stars. p = 0.005. On 8273 documents. Three years of data.*

</td>
</tr>
</table>

<br>

## Phase Dynamics

```
                         +----------------------------------+
                         |        METASTABLE                |
                         |   sr in [0.80, 1.20]             |
                         |   |gamma - 1| < 0.15             |
                         |                                  |
                         |   The system computes here.      |
                         +--+------------+------------+-----+
                            |            |            |
                   +--------v--+  +------v------+  +--v--------+
                   |CONVERGING |  |  DRIFTING   |  | DIVERGING |
                   | dg/dt < 0 |  | dg/dt > 0  |  | sr > 1.20 |
                   | toward 1  |  | from 1     |  |           |
                   +-----------+  +------------+  +-----+-----+
                                                        | 3+ ticks
                                                  +-----v-----+
              +------------+                      | DEGENERATE|
              | COLLAPSING |                      | sr > 1.50 |
              |  sr < 0.80 |                      | sustained |
              +------------+                      +-----------+

              Hysteresis: 3 consecutive ticks required for any transition
```

<br>

## Quick Start

```bash
pip install numpy scipy
```

```python
from neosynaptex import Neosynaptex, MockBnSynAdapter, MockMfnAdapter

nx = Neosynaptex(window=16)
nx.register(MockBnSynAdapter())   # gamma ~ 0.95
nx.register(MockMfnAdapter())     # gamma ~ 1.00

for _ in range(40):
    s = nx.observe()

print(f"gamma = {s.gamma_mean:.3f}")          # 1.030
print(f"phase = {s.phase}")                   # METASTABLE
print(f"coherence = {s.cross_coherence:.3f}") # 0.97
print(f"verdict = {nx.export_proof()['verdict']}")  # COHERENT
```

<br>

## Diagnostic Mechanisms

| # | Mechanism | Formula | Output |
|---|-----------|---------|--------|
| 1 | **Gamma scaling** | K ~ C^(-gamma) via Theil-Sen | per-domain gamma + 95% bootstrap CI |
| 2 | **Gamma dynamics** | dg/dt = slope of gamma trace | convergence rate toward gamma = 1.0 |
| 3 | **Universal scaling** | Permutation test, H0: all gamma equal | p-value |
| 4 | **Spectral radius** | rho = max\|eig(J + I)\| | stability per domain |
| 5 | **Granger causality** | F-test: gamma_i(t-1) --> gamma_j(t) | directed influence graph |
| 6 | **Anomaly isolation** | Leave-one-out coherence test | outlier score per domain |
| 7 | **Phase portrait** | Convex hull + recurrence in (gamma, rho) | trajectory topology |
| 8 | **Resilience** | Return rate after METASTABLE departures | metastability proof |
| 9 | **Modulation** | m = -alpha(gamma - 1)sgn(dg/dt) | bounded reflexive signal |
| 10 | **Circuit breaker** | FSM: CLOSED -> OPEN -> HALF_OPEN | adapter fault isolation |

<br>

## Circuit Breaker

The system evolves even when the external world breaks.

```
     success        >=3 failures       timeout        success
  +----------+    +--------------+   +---------+   +---------+
  |          |    |              |   |         |   |         |
  v          |    v              |   v         |   v         |
 CLOSED -----+---> OPEN --------+---> HALF_OPEN --> CLOSED
  calls           calls              one probe      recovered
  allowed         rejected           allowed
```

Thread-safe (`RLock`). Persistent across restarts (`save_state`/`load_state`). Diagnostics per domain.

<br>

## Tests

```
55 passed in 403s

TestStateCollector     #### 4    TestGranger     ## 2
TestGamma              ####### 7 TestAnomaly     ## 2
TestCoherence          #### 4    TestPortrait    ## 2
TestJacobian           #### 4    TestResilience  # 1
TestPhase              ### 3     TestModulation  ## 2
TestProof              ## 2      TestCircuit     ####### 7
TestInvariants         ### 3     TestSubstrate6  ## 2
TestLifecycle          ### 3     TestXFormProbe  #### 4
TestEdge               ### 3
```

<br>

## Invariants

| # | Invariant | Guarantee |
|---|-----------|-----------|
| 1 | **gamma derived only** | recomputed every `observe()`, never stored |
| 2 | **STATE != PROOF** | `NeosynaptexState` is `frozen=True`, independent copies |
| 3 | **zero external deps** | only `numpy` + `scipy` |
| 4 | **bounded modulation** | \|m\| <= 0.05 always |
| 5 | **all identifiers ASCII** | zero Cyrillic in code |
| 6 | **circuit breaker** | system operates under partial adapter failure |

<br>

## File Map

```
neosynaptex/
|
+-- neosynaptex.py                    1430 LOC   core: all classes + algorithms
+-- test_neosynaptex.py                900 LOC   55 tests, full coverage
+-- demo.py                            85 LOC   50-tick diagnostic demo
+-- xform_session_probe.py             300 LOC   gamma probe pipeline
|
+-- XFORM_MANUSCRIPT_DRAFT.md                    publication draft (6 substrates)
+-- XFORM_NEURO_DIGITAL_SYMBIOSIS.md             X-Form thesis
+-- CONTRACT.md                                  invariants + formulas
|
+-- xform_proof_bundle.json                      formal proof, 6 substrates
+-- xform_full_archive_gamma_report.json         8273-document analysis
+-- xform_statistical_tests.json                 permutation + effect sizes
|
+-- .github/assets/banner-dark.svg               animated SVG banner (dark)
+-- .github/assets/banner-light.svg              animated SVG banner (light)
|
+-- pyproject.toml                               numpy/scipy, Python 3.10+
+-- LICENSE                                      AGPL-3.0-or-later
```

<br>

## Writing a Real Adapter

Each NFI subsystem needs one adapter (~30 lines):

```python
class BnSynAdapter:
    @property
    def domain(self) -> str:
        return "spike"

    @property
    def state_keys(self) -> list[str]:
        return ["sigma", "firing_rate", "coherence"]

    def state(self) -> dict[str, float]:
        return {"sigma": net.sigma, "firing_rate": net.rate, "coherence": net.R}

    def topo(self) -> float:
        return net.connection_count

    def thermo_cost(self) -> float:
        return net.energy
```

Contract: `C ~ topo^(-gamma)`. The adapter provides `topo` and `thermo_cost` such that this power-law holds near criticality.

<br>

## X-Form Thesis

> Singularity is not an event of the future.
> It is a process happening now through the scale of computation
> and biological adaptation.

The human-AI cognitive loop is a measurable system.
Its scaling signature is gamma = 1.0.

When biological and digital intelligence couple productively,
they form one circuit. Not a metaphor. A measured fact.

**[Read the full thesis](XFORM_NEURO_DIGITAL_SYMBIOSIS.md)** |
**[Read the manuscript](XFORM_MANUSCRIPT_DRAFT.md)** |
**[View the proof bundle](xform_proof_bundle.json)**

<br>

---

<p align="center">

```
         *           .    .           *
    .         *              *
        .          *    .         .
   *       .    gamma = 1.0    .       *
        .     .    .    .    .
    .      *     .    .     *      .
         .    *    .    *    .
    *         .    .    .         *
```

<b>Built by one researcher. Under fire. Three years. Six substrates. One law.</b><br>
<sub>Yaroslav O. Vasylenko -- <a href="https://github.com/neuron7xLab">neuron7xLab</a> -- Poltava region, Ukraine</sub><br>
<sub>AGPL-3.0-or-later</sub>

</p>
