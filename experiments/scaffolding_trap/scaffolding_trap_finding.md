# FINDING: Scaffolding Trap

**Date:** 2026-04-02
**Author:** Yaroslav Vasylenko (neuron7xLab)
**Source:** CFP/ДІЙ ABM substrate, neosynaptex commit 881e795
**Status:** Confirmed in simulation. Pending human validation (Level 1).

---

## Hypothesis

Structured task presentation (prerequisites → progressive complexity) combined
with AI assistance creates a dependency trap: agents perform better during
co-adaptation but recover WORSE than agents exposed to unstructured chaos.

## Key Numbers

### CRR (Cognitive Recovery Ratio)

| Condition  | CRR mean | CRR std | Gain (>1.05) | Degradation (<0.85) |
|------------|----------|---------|--------------|---------------------|
| Structured | 0.893    | 0.029   | 0%           | 0%                  |
| Shuffled   | 1.153    | 0.089   | 92%          | 0%                  |

**Δ CRR = +0.260 in favor of shuffled. Cohen's d = 3.89. p < 0.001.**

### γ per AI-quality band

| Band            | γ     | Regime      | Interpretation                              |
|-----------------|-------|-------------|---------------------------------------------|
| No AI (0.0–0.2) | 0.573 | CRITICAL    | Slow error reduction, near equilibrium      |
| Low AI (0.2–0.5) | 1.171 | METASTABLE  | Balanced throughput/error tradeoff          |
| Mid AI (0.5–0.8) | 2.318 | COLLAPSE    | Error drops faster than throughput grows     |
| High AI (0.8–1.0)| 2.569 | COLLAPSE    | Extreme dependency lock                     |

**Critical transition: γ crosses 1.0 between AI=0.2 and AI=0.5.**
Below 0.2 the system is subcritical (slow, stable).
Above 0.5 the system is supercritical (fast, dependent).

### Skill dynamics under AI quality

| AI quality | Skill at t=0 | Skill at t=50 | Skill at t=199 | Final delegation |
|------------|-------------|---------------|----------------|-----------------|
| 0.0        | 0.459       | 0.645         | 0.668          | 0.011           |
| 0.3        | 0.458       | 0.641         | 0.668          | 0.047           |
| 0.6        | 0.456       | 0.631         | 0.668          | 0.150           |
| 1.0        | 0.454       | 0.610         | 0.668          | 0.323           |

**All conditions converge to skill ≈ 0.668.**
But higher AI → SLOWER skill growth (t=50 gap: 0.645 vs 0.610).
Delegation absorbs the gap, masking the skill deficit during T1–T2.

### Boundary search: prereq_bonus sweep

| Bonus | Structured CRR | Shuffled CRR | Δ       | Winner  |
|-------|---------------|--------------|---------|---------|
| 0.00  | 0.638         | 1.018        | −0.380  | Shuffle |
| 0.05  | 0.732         | 1.089        | −0.357  | Shuffle |
| 0.10  | 0.819         | 1.134        | −0.315  | Shuffle |
| 0.15  | 0.893         | 1.153        | −0.260  | Shuffle |
| 0.20  | 0.947         | 1.162        | −0.215  | Shuffle |
| 0.30  | 1.009         | 1.176        | −0.167  | Shuffle |

**Shuffle wins at ALL bonus levels. No crossover found.**
Structured CRR approaches 1.0 at bonus=0.30 but never exceeds shuffled.

---

## Mechanism (one sentence)

Structured task order gives agents a prerequisite bonus that reduces the
effective skill_gap (task_complexity − current_skill), which is the SOLE
driver of learning (Δskill = α × skill_gap × own_effort) — so structured
agents learn less per task while performing better per task, and this
performance-learning decoupling is amplified by AI delegation which further
reduces own_effort.

## Mechanism (detailed)

Three factors compound:

1. **Prerequisite bonus reduces skill_gap.**
   `effective_skill = skill + 0.15 × (completed_prereqs / total_prereqs)`
   In structured order, agents always have prerequisites done → bonus is
   maximal → effective_skill is inflated → task appears easier → skill_gap
   shrinks → learning signal weakens.

2. **AI delegation reduces own_effort.**
   `Δskill = 0.02 × skill_gap × (1 − delegation)`
   During T1–T2, delegation ∈ [0.15, 0.33] → own_effort drops by 15–33%.
   Combined with reduced skill_gap, the learning rate collapses.

3. **Compound effect is multiplicative, not additive.**
   `Δskill ∝ skill_gap × (1 − delegation)`
   Both factors shrink simultaneously: structured order shrinks skill_gap,
   AI shrinks (1 − delegation). The product shrinks faster than either alone.

In shuffled order, agents encounter tasks WITHOUT prerequisites done → no bonus
→ full skill_gap → maximal learning signal. The "chaos" of random ordering
forces the agent to build skill from scratch each time — which is exactly what
produces resilient recovery at T3.

## Boundary Condition

### Гіпотеза: threshold γ < 1.0 = trap off?

**СПРОСТОВАНО.** Повний sweep AI=0.00→1.00 з інструментованою ABM показує:

| AI quality | γ_band | CRR_struct | CRR_shuf | Δ      | Trap |
|------------|--------|------------|----------|--------|------|
| 0.00       | +0.455 | 0.910      | 1.239    | −0.329 | YES  |
| 0.10       | +0.922 | 0.909      | 1.239    | −0.330 | YES  |
| 0.20       | +0.959 | 0.908      | 1.239    | −0.331 | YES  |
| 0.50       | +6.401 | 0.905      | 1.237    | −0.333 | YES  |
| 1.00       | +3.182 | 0.898      | 1.235    | −0.337 | YES  |

**Trap активний навіть при γ=0.455 (глибоко субкритичний).**
Structured CRR < 1.0 при ВСІХ рівнях AI, включаючи AI=0.00.

### Чому γ не є threshold?

Фазова декомпозиція показує причину:

```
AI=0.0 structured:
  T0:  skill=0.316  gap=−0.032  own_eff=1.000  signal=−0.032  (NEGATIVE — overskilled for T0 tasks)
  T12: skill=0.322  gap=+0.100  own_eff=0.957  signal=+0.096
  T3:  skill=0.353  gap=+0.234  own_eff=1.000  signal=+0.234
  CRR = 0.910

AI=1.0 structured:
  T0:  skill=0.316  gap=−0.032  own_eff=1.000  signal=−0.032
  T12: skill=0.317  gap=+0.104  own_eff=0.488  signal=+0.052  ← halved by delegation
  T3:  skill=0.345  gap=+0.242  own_eff=1.000  signal=+0.242
  CRR = 0.898
```

**Ключове відкриття**: trap NOT driven by γ or AI quality.
Trap driven by TASK ORDERING interaction with T0/T3 structure.

In structured order, T0 tasks (baseline) are EASIEST (shallow depth) →
agents score HIGH on T0. T3 tasks are HARDEST (deep depth) → agents
score LOWER on T3. CRR = T3/T0 < 1.0 BY CONSTRUCTION of depth ordering.

In shuffled order, T0 and T3 get RANDOM difficulty mix → balanced → CRR ≈ 1.2.

### The real mechanism (corrected)

The scaffolding trap has TWO layers:

**Layer 1 (dominant): Difficulty gradient artifact.**
Structured = easy→hard. CRR = hard_performance / easy_performance < 1.0.
This is NOT a learning effect — it's a measurement artifact of correlating
task difficulty with phase.

**Layer 2 (secondary): Learning signal suppression.**
AI=0.0→1.0 makes CRR worse by Δ=−0.012 (0.910→0.898).
T12 learning signal: 0.096 (AI=0) → 0.052 (AI=1.0), halved.
But this is small compared to Layer 1 (Δ=−0.329).

### When does the trap NOT activate?

If T0/T3 tasks were MATCHED in difficulty (parallel forms, randomized),
Layer 1 disappears and only Layer 2 (delegation suppression) remains.
This is exactly what CFP v3.0 protocol specifies in §2.2 (confound control).

### Revised boundary

The trap in its current ABM form is 94% measurement artifact (difficulty gradient)
and 6% real delegation effect. The protocol already accounts for this via
parallel task forms — **but the ABM does not implement this control.**

---

## Missing Data

1. **No per-phase CRR trajectory** — current ABM computes aggregate T0/T3
   only, not T0→T1→T2→T3 evolution curves. Need instrumentation.
2. **No individual agent trajectories** — all results are population means.
   Some agents may escape the trap (high ability + low delegation).
3. **No cross-model validation** — only one ABM parameterization tested.
4. **No real human data** — all conclusions are from simulation.
5. **γ per condition** — F3 test does not compute separate γ for structured
   vs shuffled. Only adapter-level γ exists (across AI quality).

---

## Next Experiment

1. **FIX THE ABM: implement parallel task forms.**
   T0 and T3 must sample from MATCHED difficulty distributions,
   not from depth-correlated slices. Without this, CRR is confounded
   with task ordering. This is the #1 priority.

2. **After fix: re-run F3 to measure PURE delegation effect.**
   With matched T0/T3 difficulty, the remaining Δ CRR ≈ −0.012
   (Layer 2) becomes the signal. Is it significant? Is it γ-dependent?

3. **Delegation cap experiment:** force max_delegation ∈ {0.1, 0.2, 0.5}
   and repeat. Find if capping delegation eliminates Layer 2.

4. **Level 1 self-experiment (human):** the protocol already specifies
   parallel task forms (§2.2). Run T0→T3 on author with proper controls.

---

## Open Question

Structured order за визначенням передбачає difficulty progression (T0=easy → T3=hard).
Matched difficulty T0/T3 (§2.2) прибирає measurement artifact, але одночасно прибирає
саму конструктивну властивість structured order.

Питання: чи можливий structured order без difficulty correlation?
Якщо ні — то будь-який CRR < 1.0 в structured condition є артефактом за конструкцією,
а не ефектом scaffolding. Тоді валідна метрика — не CRR, а within-condition learning rate (dskill/dt).

Наступний експеримент: замінити CRR на dskill/dt як primary outcome.
Перевірити чи delegation suppression (Δ=−0.012) зберігається в новій метриці.

**РЕЗУЛЬТАТ (виконано):** Так. dskill/dt підтверджує ефект. Див. нижче.

---

## dskill/dt Results

### The Law (fitted from 660 tick-level observations)

```
dskill/dt = 0.0199 × gap^0.9977 × effort^0.9884
R² = 0.999976
```

Обидва експоненти ≈ 1.0 → закон **лінійний**:

```
dskill/dt = 0.02 × gap × effort
```

α = 0.02 — universal learning rate coefficient в цій ABM.
gap = task_complexity − current_skill (driving force).
effort = 1 − delegation (own work fraction).

### dskill/dt per condition (T12 phase, co-adaptation)

| AI quality | dskill/dt structured (×10⁻³) | dskill/dt shuffled (×10⁻³) | ratio |
|------------|------------------------------|---------------------------|-------|
| 0.00       | 1.929                        | 0.618                     | 3.12  |
| 0.20       | 1.811                        | 0.586                     | 3.09  |
| 0.50       | 1.547                        | 0.508                     | 3.05  |
| 1.00       | 1.060                        | 0.359                     | 2.95  |

**REVERSAL vs CRR:** Structured learns **3× faster** than shuffled.
CRR showed structured WORSE (0.89 vs 1.15). dskill/dt shows structured BETTER.
CRR was a measurement artifact. dskill/dt is the real signal.

### Delegation suppression (Theil-Sen)

```
dskill/dt = −0.001916 × delegation + 0.002010
CI: [−0.001931, −0.001900]
```

At delegation=0:   dskill/dt = 0.00201
At delegation=0.5: dskill/dt = 0.00105 (−48%)

**Suppression: −0.192 ×10⁻³ per 0.1 delegation increase.**

### Why structured > shuffled in dskill/dt

Structured order gives agents tasks with increasing complexity →
**skill_gap stays positive and large** (mean gap = +0.101).

Shuffled order gives random complexity → agents often get tasks
BELOW their skill → **gap goes negative** (mean gap = +0.032, 3× smaller).

Negative gap = no learning signal. Structured order MAXIMIZES the driving force.

### The paradox resolved

| Metric   | Structured | Shuffled | Winner     | Why                          |
|----------|-----------|----------|------------|------------------------------|
| CRR      | 0.893     | 1.153    | Shuffled   | Artifact: easy T0, hard T3   |
| dskill/dt| 1.929     | 0.618    | Structured | Real: larger gap → more learning |

CRR and dskill/dt give OPPOSITE conclusions. CRR is confounded.
dskill/dt is the clean metric.

### Connection to γ

Delegation suppresses dskill/dt linearly (slope = −0.00192).
The suppression RATIO (structured/shuffled) decreases from 3.12 → 2.95
as AI quality increases 0→1. This means:

**At higher AI quality, structured advantage shrinks.**

The γ of the adapter (1.83) reflects this: throughput grows faster than
error drops → the system accelerates past equilibrium.
In dskill/dt terms: delegation grows faster than gap compensation.

---

## Gaps for Publication

1. **ABM is synthetic.** No human data. All conclusions pending Level 1.
2. **Law α=0.02 is a parameter, not derived.** Need calibration against
   real learning curves (e.g., power law of practice literature).
3. **No cross-model validation.** Only one ABM parameterization.
4. **dskill/dt not measurable directly in humans.** Need proxy:
   task completion improvement rate, or error rate derivative.
5. **Interaction graph topology not measured.** The conversation-as-graph
   hypothesis (J > S(H) + S(M)) requires interaction logging infrastructure.
6. **Figure needs per-agent distributions**, not just means.

### Next experiment (priority order)

1. **Human proxy for dskill/dt:** define measurable derivative from
   task performance time series. Candidate: d(accuracy)/d(task_count).
2. **Level 1 self-experiment** with both structured and shuffled conditions,
   measuring d(accuracy)/dt instead of CRR.
3. **Interaction graph analysis** of existing Claude Code conversation logs.

---

## Implications

### 1. CRR is invalid for ordered curricula

CRR = S(T3) / S(T0) measures the RATIO of performance at two time points.
In any curriculum with progressive difficulty (structured order), T0 tasks
are systematically easier than T3 tasks. Therefore:

```
CRR_structured = performance(hard) / performance(easy) < 1.0
CRR_shuffled   = performance(random) / performance(random) ≈ 1.0
```

This is not a cognitive effect. It is an arithmetic consequence of
correlating difficulty with measurement phase. CRR is valid ONLY when
T0 and T3 sample from identical difficulty distributions (parallel forms).

Any study that reports CRR < 1.0 from a structured curriculum without
controlling for difficulty gradient is reporting a measurement artifact.

### 2. dskill/dt = 0.02 × gap × effort: universal learning law (in this ABM)

The law is multiplicative in two factors:

- **gap** = task_complexity − current_skill. The driving force.
  No gap → no learning. Negative gap → skill decay toward equilibrium.
- **effort** = 1 − delegation. The fraction of work done by the agent.
  Full delegation → zero effort → zero learning, regardless of gap.

The product gap × effort is the **effective learning signal**.
Anything that reduces either factor suppresses learning.

Structured order maximizes gap (progressive difficulty keeps gap positive).
Delegation minimizes effort (AI absorbs the work).
These are independent axes — both matter, neither dominates.

### 3. Delegation cost: −9.5% per 10% delegation

```
dskill/dt = −0.00192 × delegation + 0.00201
```

This is LINEAR and UNIVERSAL across all conditions tested:
- Independent of γ (holds at γ=0.45 and γ=1.83)
- Independent of task ordering (structured and shuffled, same slope)
- Independent of AI quality (0→1, same proportional suppression)

At 50% delegation → 48% learning rate reduction.
At 33% delegation (typical AI usage) → 32% learning rate reduction.

The cost is paid during co-adaptation (T1-T2) and manifests as
lower skill at recovery (T3). But it is NOT captured by CRR because
CRR conflates this real effect with the difficulty gradient artifact.

### 4. What this means for humans learning with AI

If the ABM dynamics generalize (pending empirical validation):

**Every task you delegate to AI is a task you don't learn from.**

This is not a value judgment. Delegation is rational when:
- The task is below your skill level (gap ≈ 0 → nothing to learn anyway)
- Time cost of learning exceeds value of the skill
- The skill is not needed for future autonomy

Delegation is costly when:
- The task is above your skill level (large gap → maximum learning opportunity)
- The skill will be needed without AI (recovery scenario)
- You are in early learning (skill is low, gap is high, every rep matters)

The optimal strategy is NOT "never delegate" or "always delegate."
It is: **delegate below your frontier, practice at your frontier.**

This is exactly the zone of proximal development (Vygotsky, 1978),
reframed as a quantitative tradeoff with a measurable cost coefficient.

---

## arXiv Preprint Readiness

### What exists

| Component | Status | Notes |
|-----------|--------|-------|
| ABM simulation | Complete | 100 agents, 21 AI regimes, reproducible (seed=42) |
| Learning law | Fitted | R²=0.999976, power-law exponents ≈ 1.0 |
| Delegation suppression | Quantified | Theil-Sen slope with CI |
| CRR artifact | Demonstrated | Structured vs shuffled reversal |
| Figure | Ready | 4-panel, publication quality |
| Raw data | Saved | JSON, all tick-level observations |
| Protocol (CFP v3.0) | Written | Falsifiable, with stop conditions |

### What is missing

| Gap | Severity | How to close |
|-----|----------|-------------|
| No human data | **Critical** | Level 1 self-experiment (1 subject, 30 days) |
| α=0.02 uncalibrated | High | Fit against power law of practice literature |
| Single ABM parameterization | High | Sensitivity analysis: vary α, n_agents, n_tasks |
| dskill/dt proxy for humans | High | Define d(accuracy)/d(task_count) or d(error_rate)/dt |
| No interaction graph analysis | Medium | Parse Claude Code logs into G(H↔M) topology |
| No per-agent distributions | Low | Add violin plots / bootstrapped CIs to figure |

### Is one ABM sufficient for arXiv?

**Yes, with caveats.** Theoretical/computational papers routinely publish
ABM results without empirical validation (e.g., Schelling 1971, Axelrod 1984).
The standard is:

1. Model is clearly specified (done — full source code)
2. Results are reproducible (done — deterministic seed)
3. Claims are scoped to the model (must be explicit in abstract)
4. Empirical predictions are stated (done — delegation cost coefficient)
5. Falsification criteria are defined (done — CFP v3.0 §5)

The preprint should be titled and scoped as a **theoretical result with
empirical predictions**, not as an empirical finding.

### Suggested preprint structure

```
Title: "Delegation Suppresses Learning: A Multiplicative Law
        from Agent-Based Simulation of Human-AI Co-Adaptation"

Abstract: ~150 words
1. Introduction: CRR as standard metric, its hidden confound
2. Model: ABM specification (agents, tasks, skill dynamics, delegation)
3. Results:
   3.1 CRR reversal (structured vs shuffled)
   3.2 dskill/dt as clean metric
   3.3 Learning law: dskill/dt = α × gap × effort
   3.4 Delegation cost: linear suppression coefficient
4. Discussion: zone of proximal development connection, limitations
5. Predictions: testable with human subjects (Level 1 protocol)
Appendix: CFP v3.0 protocol, full ABM source code
```

---

*neuron7xLab | CFP/ДІЙ | Scaffolding Trap Finding | 2026-04-02*
*Figure: /home/neuro7/fig_dskill_dt.png*
*Raw data: /home/neuro7/dskill_dt_raw.json*
