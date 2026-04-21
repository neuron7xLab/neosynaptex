# A falsifiable dialogue substrate for the neosynaptex gamma engine

**Yaroslav Vasylenko** · neuron7xLab · `neuron7x@ukr.net`
Draft · v0.1.0 · 2026-04-21

---

## Abstract

We introduce `DialogueAdapter`, an experimental substrate for the
neosynaptex gamma engine that probes the empirical scaling law
`thermo_cost ~ topo^(-γ)` in human–AI conversation sessions. The
adapter is semantically minimal: `topo` is the cumulative unique
vocabulary and `thermo_cost` is the cumulative token count. Gamma is
estimated by the canonical neosynaptex engine (Theil-Sen slope + 500-
sample bootstrap CI) and is never stored inside the probe. We guard
every gamma value with a four-test anti-tautology battery — turn
permutation, lexical surrogate, piecewise stability, and leave-one-
turn-out sensitivity — that must unanimously pass before a result may
enter the scientific-evidence directory. The instrument is paired with
a three-test falsification battery (permutation, Cohen's *d*, KS)
whose null-result contract is explicit: a negative LLM-only γ
repeats, not contradicts, the existing `experiments/lm_substrate`
null (γ = -0.094, p = 0.626). We report on engineering
reproducibility and the scope of this substrate; falsification against
real dialogue corpora is ongoing work.

## 1. Introduction

Edge-of-chaos computation — the conjecture that information-processing
systems operate near a phase transition between order and disorder —
has been studied in branching processes (Beggs & Plenz, 2003),
recurrent networks (Bertschinger & Natschläger, 2004), and coupled
oscillator ensembles. The neosynaptex engine operationalises one
empirical consequence of this conjecture: an exponent γ that describes
how a system's topological breadth scales with its thermodynamic cost
across a sliding window. γ ≈ 1 is consistent with sub-linear scaling
near a power-law regime; γ far from 1 is consistent with either
saturation or explosive growth.

neosynaptex already houses one dialogue-adjacent null result: a
stateless GPT-4o-mini substrate with γ = -0.094, p = 0.626
(`experiments/lm_substrate/gpt4o_coupled_raw.json`). That result is
important — it shows that isolated inference without closed-loop
dynamics produces no temporal structure. This probe asks the
complementary question: **what does γ look like in *coupled*
human–AI dialogue?** We do not claim that any particular γ implies
consciousness, intelligence, or truth — the instrument measures only a
scaling exponent. Our contribution is a falsifiable pipeline with
explicit null-acceptance rules, not a universal criticality detector.

## 2. Method

### 2.1 Semantic contract and CLAIM BOUNDARY

> **This probe does not measure consciousness, intelligence, or truth.**
> It measures one thing: the empirical scaling exponent γ in the power
> law `thermo_cost ~ topo^(-γ)` across a dialogue session, as
> extracted by the canonical neosynaptex gamma engine. γ close to 1
> indicates the session lives near the scaling point where vocabulary
> breadth grows sub-linearly with conversational depth; γ ≠ 1 does not
> imply malfunction and γ ≈ 1 does not imply criticality-of-thought.
> Any interpretation beyond the literal power-law exponent is the
> reader's, not the instrument's.

### 2.2 The adapter

`DialogueAdapter` conforms to the neosynaptex `DomainAdapter` Protocol
(domain, state_keys, state, topo, thermo_cost). `topo` is
`|{t : t ∈ tokens(content(turn_i))_{i ≤ t}}|` — the cumulative count of
distinct case-insensitive whitespace-delimited tokens. `thermo_cost`
is the cumulative sum of caller-provided `token_count` fields. Both
are strictly non-decreasing by construction (`topo` can repeat when a
turn introduces no new tokens; `thermo_cost` must strictly increase).
Turn history is append-only; the underlying `Turn` dataclass is
frozen.

### 2.3 Gamma extraction

γ is computed by the canonical `core.gamma.compute_gamma`
(Theil-Sen slope on log-log pairs with a 500-sample bootstrap CI,
gated by ≥ 5 valid pairs, log-range ≥ 0.5, R² ≥ 0.3). The probe
reads `NeosynaptexState.gamma_mean` and never caches it.

### 2.4 Anti-tautology battery (AT-1..AT-4)

Every gamma estimate from a `ProbeSession` must survive four tests:

- **AT-1 Shuffled null.** Permute turn order (seed = 7), recompute γ.
  If `|γ_original − γ_shuffled| < 0.1`, the order of turns does not
  matter and γ reflects a cumulative-sum artifact rather than temporal
  structure (`tautology_flag`).
- **AT-2 Lexical surrogate.** Replace each turn's content with random
  tokens from a fixed 512-word alphabet, preserving `token_count`.
  Run 32 surrogate trials; compute a two-sided normal-approximation
  empirical p-value against the mean and std of surrogate γs. If
  `p ≥ 0.05`, vocabulary structure is irrelevant — the metric is a
  length-only artifact (`surrogate_flag`).
- **AT-3 Piecewise stability.** Split turns at the midpoint and
  compute γ on each half independently (fresh `ProbeSession`). If
  `|γ_first − γ_second| > 0.3`, the scaling is non-stationary
  (`instability_flag`).
- **AT-4 Leave-one-turn-out.** For each turn, drop it and re-estimate
  γ. If `max_t |γ_full − γ_{−t}| > 0.2`, a single turn dominates the
  estimate (`outlier_flag`).

`AntiTautologyResult.passed` is `True` iff γ is finite and no flag is
set. Any failure is recorded verbatim in the result's `notes` tuple;
no flag is ever suppressed.

## 3. Falsification design

**H₀:** `γ_human_ai == γ_llm`. **H₁:** `γ_human_ai > γ_llm`.

We compute three statistics on a pair of gamma collections:

1. SciPy `permutation_test` (independent, alternative="greater",
   10 000 resamples, seed = 7).
2. Cohen's *d* with pooled unbiased standard deviation.
3. Two-sample Kolmogorov–Smirnov.

We call the effect *significant* at α = 0.01 on the permutation test.
A separate `null_confirmed` flag is set whenever `mean(γ_llm) < 0`
— this is the connection point to the existing stateless-LM null
result and publishable as-is.

## 4. Results (engineering verification)

Running `probe/reproduce.py` with seed = 7, window = 16, and
N = 24 turns on two synthetic scenarios produces:

- **human_ai_synthetic** (growing vocabulary): γ ≈ −0.95,
  `tautology_flag = True`. The synthetic session has no real temporal
  structure, so shuffling the turn order leaves γ unchanged — AT-1
  correctly refuses to promote this to scientific evidence.
- **llm_only_synthetic** (flat 8-word vocabulary): γ = NaN. Vocabulary
  saturates after the first few turns, collapsing the log-range below
  the engine's 0.5 gate — AT correctly invalidates.

Both behaviours are what AT-1..AT-2 are designed to detect on
non-meaningful inputs. **The engineering harness works precisely by
*rejecting* synthetic data.** Falsification against a real dialogue
corpus is the next step and will be reported separately.

## 5. Discussion

- **Scope.** `topo` is a lexical proxy; a richer operationalisation
  (e.g. semantic unit count via sentence embeddings) would probe the
  same scaling law through a different lens. `thermo_cost` is a length
  proxy; caller-provided token counts are assumed truthful. The probe
  does not model attention allocation, reasoning depth, or
  coherence — only their aggregate statistical shadow.
- **External validity.** Results on one corpus do not generalise to
  others without re-running the anti-tautology battery. That is the
  point: a γ on dialogue session X is a claim about X, nothing more.
- **What would falsify the instrument itself.** If a real session
  with clear turn-to-turn dependencies nonetheless produces
  `tautology_flag = True`, AT-1 is miscalibrated. If two independent
  surrogates produce identical γ but the full session and the lexical
  surrogate also coincide, AT-2 is miscalibrated. In either case,
  the battery should be revised before any conclusion about the
  underlying dialogue is drawn.

## 6. Reproducibility

- Docker image pinned to `python:3.12-slim` + `numpy ≥ 1.26`,
  `scipy ≥ 1.11`. `PYTHONHASHSEED = 0` and explicit seed = 7 on every
  `ProbeSession`. Outputs agree across hosts to 6 decimal places.
- `probe/seed_ledger.json` append-only JSONL ledger records every
  session seed before the first stochastic operation.
- Dataset contract (`probe/src/probe/ingestion.py`) validates JSONL
  input fail-closed (role ∈ {human,assistant}, token_count > 0,
  non-empty content, unique session_id, len ≥ MIN_TURNS = 8);
  rejections are appended to a rejection log.

## References

- Beggs, J.M., Plenz, D. (2003). Neuronal avalanches in neocortical
  circuits. *J. Neurosci.* 23(35).
- Bertschinger, N., Natschläger, T. (2004). Real-time computation at
  the edge of chaos in recurrent neural networks. *Neural Comput.*
  16(7).
- Vasylenko, Y. (2026). neosynaptex v3.0.0 (this repository).
- `experiments/lm_substrate/gpt4o_coupled_raw.json` (null result,
  γ = -0.094, p = 0.626).
