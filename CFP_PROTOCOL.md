# COGNITIVE FIELD PROTOCOL (CFP v3.0) — CANONICAL ENGINEERING SPEC

**Codename:** ДІЙ
**Class:** Cognitive Measurement Protocol
**Type:** Deterministic / Falsifiable / Cross-Substrate
**Authoring Standard:** Audit-grade, fail-closed
**Author:** Yaroslav Vasylenko | neuron7xLab
**Date:** 2026-04-02

---

## /TASK

Визначити, чи змінює обчислювальний контур (людина + AI) **структуру когніції** суб'єкта, та чи є ця зміна:

* відновлюваною (інструмент)
* незворотною (заміщення)

Кінцева мета:

> Встановити, чи є **когніція функцією топології взаємодії**, а не властивістю суб'єкта.

---

## /SCOPE

**Система:**

* Human node (H)
* Model node (M)
* Dataset topology (D)
* Interaction graph G(H<->M)

**Режими:**

* Solo cognition (baseline)
* Co-adaptive cognition (interaction)
* Post-interaction cognition (recovery)

**Інваріант:**

* CRR (Cognitive Recovery Ratio)

---

## /FORMAL MODEL

```math
S(T3) = f(D, M, G_{T1->T2}) + e
```

де:

* S -- когнітивна складність
* D -- топологія датасету
* G -- граф взаємодії
* e -- шум

---

## /CORE HYPOTHESIS

> H1: Існує детермінований вплив топології D на S, що зберігається після відключення M.

---

## /EXPERIMENT PIPELINE

```
T0 -> T1 -> T2 -> T3
```

### T0 -- BASELINE (solo)

* без моделі
* задачі контрольного набору
* фіксація: LD0, TC0, DT0

### T1 -- ONSET (co-adaptation)

* стандартна взаємодія
* збір: DI, структура запитів, latency

### T2 -- DEEP LOOP

* стабілізація патернів
* вимір: compression vs simplification, CPR trajectory

### T3 -- RECOVERY (critical phase)

* повне відключення системи
* задачі: baseline-equivalent, novel complex, divergent mandatory

---

## /METRICS

### Primary

```
CRR = S(T3) / S(T0)
S = w1*LD + w2*TC + w3*DT
```

### Diagnostic

| Metric | Function               |
|--------|------------------------|
| LD     | lexical diversity      |
| TC     | task complexity        |
| DT     | divergent thinking     |
| DI     | dependency             |
| CPR    | compression primitives |

### State Classification

| CRR       | State          |
|-----------|----------------|
| >1.05     | Cognitive Gain |
| 0.95-1.05 | Neutral        |
| 0.85-0.95 | Compression    |
| <0.85     | Degradation    |

---

## /CRITICAL TEST (BINARY)

```
Recovery Test:
Does S(T3) ~ S(T0)?
```

* YES -> tool
* NO -> system change

---

## /TOPOLOGY LAW TEST

### F3 (KILL SWITCH)

```
CRR(D_structured) != CRR(D_shuffled), p < 0.01
```

### M4 (PROOF)

```
CRR(D_10%) ~ CRR(D_100%), p > 0.05
```

---

## /GAMMA INTEGRATION

```
gamma-CRR ~ 1.0 -> metastable regime
```

Conditions:

* Theil-Sen slope
* bootstrap CI95
* permutation test (10^4)
* For fBm: gamma_PSD = 2H + 1 (NEVER 2H - 1)

---

## /VALIDATION

### Internal

* A/B parallel task forms
* blind T3 evaluation
* test-retest reliability CRR > 0.8

### External

* multi-model (GPT, Claude, local LLM)
* multi-domain (science, engineering, business)
* IQ independence (CRR not correlated with IQ)

---

## /FALSIFICATION

| Condition              | Result                |
|------------------------|-----------------------|
| F1: CRR invariant      | no effect             |
| F2: CRR collapse       | universal degradation |
| F3: no topology effect | hypothesis dead       |
| F4: gamma mismatch     | no universality       |

---

## /NETWORK POLICY

* No hidden state inference
* Only observable outputs
* External-only measurement
* Deterministic logging

---

## /OUTPUT ARTIFACTS

1. CRR distribution
2. CPR trajectory
3. LD / TC / DT raw logs
4. F3 comparison
5. gamma-CRR estimation

---

## /STOP CONDITIONS

Execution stops if:

* F3 fails
* CRR not reproducible
* CPR inconsistent

---

## /NFI SUBSTRATE INTEGRATION

```
NFI Substrate Map:
+-- Biological:    Zebrafish (McGuirl 2020)     gamma = +1.055
+-- Morphogenetic: MFN+ (Gray-Scott)            gamma = +0.979
+-- Oscillatory:   mvstack (Kuramoto)            gamma = +0.963
+-- Neural:        BN-Syn / DNCA                 gamma = +0.946
+-- Cognitive:     CNS-AI Loop                   gamma = +1.059
+-- Co-adaptive:   CFP/DIY (human+AI)            gamma = +1.832 (CONSTRUCTED, ABM)
```

### Contracts

* gamma derived only, never assigned
* STATE != PROOF (CRR state != topology law proof; proof = F3 test)
* SSI external only
* Bounded modulation (CPR drift > threshold -> recalibrate)

---

## /EVOLUTION

| Level | Scope | Deliverable |
|-------|-------|-------------|
| 1     | N=1 self-experiment | CRR, CPR, preliminary gamma-CRR |
| 2     | N=12-20 pilot | CRR distribution, Cohen's d, F3+M4 |
| 3     | Multi-domain validation | Universality claim |
| 4     | Infrastructure protocol | Open toolchain, API |

---

## /FINAL STATEMENT

> Cognition is not an entity property.
> It is a **topological state of interaction**.

---

## /MINIMAL FORMULA

```
Cognition = f(Topology)
```

---

## /SYSTEM STATUS

* Before validation -> Hypothesis
* After F3 + M4 -> Law candidate
* After cross-substrate gamma alignment -> Universal principle

---

## /IMPLEMENTATION

Code: `substrates/cfp_diy/`

| File | Purpose |
|------|---------|
| `adapter.py` | ABM simulation: 50 agents, 25 AI-quality regimes, emergent gamma |
| `metrics.py` | CRR, CPR, MTLD, S-score, gamma-CRR (PSD + Theil-Sen) |
| `protocol.py` | T0->T3 experiment engine (ready for Level 1 real data) |
| `topology_law.py` | F3 kill switch + M4 test (both ABM-based) |

Tests: `tests/test_cfp_diy.py` -- 37 tests (incl. 5 scientific integrity guards)

### Current ABM Results (CONSTRUCTED -- not real data)

```
gamma  = 1.832  (COLLAPSE zone, NOT metastable)
R2     = 0.853
CI95   = [1.638, 1.978]
p_perm = 0.000
```

Interpretation: In this ABM, error rate drops faster than throughput grows
as AI quality increases. The system is NOT in metastable equilibrium.
This is a legitimate scientific finding from the simulation --
real human data may produce different gamma.

### Scientific Integrity Guards

1. AST scan: no `gamma = <float>` assignments in adapter source
2. No `topo**(-x)` power-law injection
3. ABM tracks skill/delegation/error dynamics
4. Ledger status = CONSTRUCTED (not VALIDATED)
5. gamma is whatever the simulation produces

---

*neuron7xLab | Cognitive Field Protocol v3.0 | Codename: DIY | 2026-04-02*
