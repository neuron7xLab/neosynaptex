# Horizon Knobs — Per-Substrate Operational Definitions

**Protocol reference.** `docs/protocols/levin_bridge_protocol.md` Step 3 & Step 7.

**Role.** Each substrate entry below defines the **single code parameter (or smallest coupled set)** that moves the effective integration horizon **H**. Without these definitions, Steps 4–8 cannot start.

**Rule.** Every knob cites an `evidence/` commit SHA at the moment of pre-registration, per `evidence/PREREG.md` conventions. No row may be appended to `cross_substrate_horizon_metrics.csv` unless the adapter code that produces it existed at the pre-registered SHA or earlier.

**Substrates in scope after audit.** Three — MFN+, Kuramoto, BN-Syn. The **LLM multi-agent** substrate is explicitly scoped out of the bridge at this time; see final section for the existing falsification record and the conditions under which it may re-enter.

---

## 1. MFN+ (`substrates/mfn/`)

**Canonical entrypoint.**
`substrates/mfn/src/mycelium_fractal_net/core/engine.py::run_mycelium_simulation_with_history(config: SimulationConfig) -> SimulationResult`

**Horizon knob.** `config.alpha` — reaction–diffusion coupling coefficient.

- Field: `SimulationConfig.alpha` (`core/types.py:57`).
- Default: `0.18` (`core/reaction_diffusion_config.py:22`, `DEFAULT_FIELD_ALPHA`).
- Type: `float`.
- Code-enforced bounds: `ALPHA_MIN = 0.05`, `ALPHA_MAX = 0.25` (`reaction_diffusion_config.py:36–37`). CFL hard ceiling `MAX_STABLE_DIFFUSION = 0.25` (`reaction_diffusion_config.py:46`).
- Consumption site: `engine.py:244–248` — `field += alpha * effective_dt * laplacian`.
- Justification: `alpha` directly governs the spatiotemporal reach of diffusive influence. Matches protocol Step 7 definition for MFN+: "diffusion / coupling radius."

**Three regimes.**

| Regime | `alpha` | Code-ground |
|---|---|---|
| Compressed | `0.08` | Above `ALPHA_MIN=0.05` with margin; sub-default diffusion. |
| Intermediate | `0.18` | Factory default (`config_validation.py:275`). |
| Expanded | `0.24` | Just below CFL ceiling `0.25`; `alpha_guard` (`engine.py:351–365`) enabled by default. |

**Productivity proxy P.** `SimulationResult.growth_events` (`types.py:244`) — count of spike nucleation events accumulated in `_simulation_step` (`engine.py:233`). Viability rule: every regime run MUST satisfy `growth_events > 0` across the measurement window; otherwise the regime is non-productive and does not enter the analysis.

**Gaps.**
- `config.adaptive_alpha` (default `True`, `reaction_diffusion_config.py:130`) allows per-cell `alpha` modulation via STDP-like rules (`ALPHA_LTP_RATE`, `ALPHA_LTD_RATE`, `config.py:42–43`). For the bridge run, set `adaptive_alpha=False` to isolate the horizon manipulation. Document the fixed value in the row.
- Compressed regime may under-sample the Turing threshold and stall pattern formation for certain seeds; seeds with zero `growth_events` are discarded and replaced, not silently averaged in.
- Expanded regime near-CFL: log `alpha_guard` activations per row.

---

## 2. Kuramoto (`substrates/kuramoto/`)

**Caveat — read first.** The `substrates/kuramoto/` tree does **not** contain a canonical Kuramoto oscillator simulator of the form `dθ/dt = ω + K·Σsin(θⱼ − θᵢ)`. It is the **TradePulse** market-regime analytics platform, which uses a Kuramoto-inspired coherence proxy **Δr** over financial return series. The protocol therefore operationalises H on the **proxy** system, not on a classical oscillator network. This caveat is non-trivial and must be restated in any manuscript that cites Kuramoto-substrate results.

**Canonical entrypoint.**
`substrates/kuramoto/analytics/regime/src/core/tradepulse_v21.py::TradePulseV21Pipeline.run()` (lines 742–799).

**Horizon knob (tuple).** `FeatureBuilderConfig.window` + `FeatureBuilderConfig.ema_alpha`.

- `window` — lookback span in trading days. Default `252` (`tradepulse_v21.py:153`). Controls the temporal window over which Δr is accumulated (`tradepulse_v21.py:280–282`).
- `ema_alpha` — decay of the coherence smoother. Default `0.2` (`tradepulse_v21.py:158`). Lower `ema_alpha` → longer effective memory of past coherence.
- Constraint: `len(returns) >= window + horizon` (`tradepulse_v21.py:280`).

**Three regimes.**

| Regime | `window` | `ema_alpha` | Code-ground |
|---|---|---|---|
| Compressed | `21` | `0.05` | ~1 month; fast α → shallow memory. Within observed test-fixture range (`test_tradepulse_v21.py` uses 30/40/90). |
| Intermediate | `63` | `0.15` | ~1 quarter; balanced. |
| Expanded | `252` | `0.30` | Annual default; slow α deepens memory weighting. |

**Productivity proxy P.** `ModelPerformance.auc` from `LogisticIsotonicTrainer` (`tradepulse_v21.py:317–325`), reported via `PipelineResult.to_dict().artifacts.performance.auc` (lines 687–699). This measures whether wider H actually **improves regime forecasting** — a real task metric, not a self-referential synchrony measure. Viability rule: `auc > 0.55` on held-out folds per regime; otherwise regime is non-productive.

**Gaps.**
- Coherence `_coherence()` (`tradepulse_v21.py:177`) uses FFT phase alignment; not formally validated against classical Kuramoto order parameter `R = |Σexp(iθⱼ)|/N`. Flag this in any cross-substrate comparison.
- `ema_alpha` couples to memory length AND high-frequency-noise smoothing; cannot be cleanly attributed to H alone without ablation (vary `window` at fixed `ema_alpha`, then vice versa).
- Rank normalisation of H across substrates is unspecified; for Kuramoto-proxy, rank by `window` days only.

---

## 3. BN-Syn (`substrates/bn_syn/`)

**Canonical entrypoint.**
`substrates/bn_syn/src/bnsyn/sim/network.py::Network` (class declared at line 99; step loop at `network.py:217–245`).

**Horizon knob (tuple).** `p_conn` + `delay_ms` + `tau_NMDA_ms`. All three together define the protocol's BN-Syn H triple: "temporal memory depth, recurrence span, coupling reach." `max_memories` is held fixed at the intermediate value to isolate the dynamics-level horizon from the sleep-consolidation-level horizon.

- `p_conn` — connection probability (`sim/network.py:88`). Default `0.05`. Type `float`. Controls graph density and therefore coupling reach.
- `delay_ms` — synaptic transmission delay (`config.py:113`). Default `1.0` ms. Controls recurrence span.
- `tau_NMDA_ms` — NMDA dendritic integration time constant (`config.py:110`). Default `100.0` ms. Controls temporal integration window.

**Three regimes.**

| Regime | `p_conn` | `delay_ms` | `tau_NMDA_ms` | Justification |
|---|---|---|---|---|
| Compressed | `0.01` | `0.5` | `20` | Sparse coupling, shallow recurrence, narrow temporal integration. |
| Intermediate | `0.05` | `1.0` | `100` | Repository defaults. |
| Expanded | `0.10` | `2.0` | `200` | Dense recurrence, extended integration; within physiologically plausible range cited in `bn_syn` literature docs. |

Fixed across regimes: `max_memories = 200` (`sleep/cycle.py:76` default). Any regime that requires varying `max_memories` is a different study and must be registered separately.

**Productivity proxy P.** Composite from `Network.step()` return dict (`network.py:217–245`):

1. **Criticality σ** (`sigma`, branching ratio) — target `σ ≈ 1.0`. Bridge run discards any regime whose median `σ` is outside `[0.85, 1.15]` as non-productive (sub-critical die-off or super-critical saturation).
2. **Spike rate** (`spike_rate_hz`) — must be non-zero and stationary over the measurement window.

Optional secondary: replay-accuracy from `sleep/replay.py` and assembly-detection reliability from `assembly/detector.py`. These are reported but not gating.

**Gaps.**
- Interaction between `p_conn` and criticality `σ` is nonlinear; expanded `p_conn=0.10` may drift network super-critical unless homeostatic scaling is enabled. Confirm by measuring `σ` time series per regime, not just endpoint.
- `tau_NMDA_ms` coupling to H is partially confounded by eligibility-trace `tau_e_ms=500.0` (`config.py:148`); hold `tau_e_ms` fixed across regimes.
- Adapter code for bridge measurement MUST be committed and pre-registered per `evidence/PREREG.md` before any row is appended; location TBD (candidate: `substrates/bn_syn/src/bnsyn/benchmarks/` or a new `bridge/` module).

---

## 4. LLM multi-agent — **scoped out**

**Status.** Excluded from the bridge at this iteration. The existing experimental record already falsifies the bridge claim for the available LLM surface.

**Evidence in-repo.**

- `experiments/lm_substrate/claude_substrate_experiment.py`, `experiments/lm_substrate/gpt4o_substrate_experiment.py`, `experiments/lm_substrate/README.md`.
- GPT-4o-mini run: `γ = 0.214`, `p = 0.203`, 95 % CI crosses zero — COLLAPSE regime.
- README (`experiments/lm_substrate/README.md:18–19`): *"γ ≈ 0 in all conditions. API-level LLM inference is stateless — no temporal coupling between calls."*

**Why it cannot be a bridge substrate as currently coded.**

- Only tuneable knobs are `temperature` and `max_tokens`. Neither maps to the protocol's H definition (memory span, communication graph depth, steps over which information remains causally active).
- Stateless API calls have no inter-step state coupling — there is no substrate on which H can be *manipulated*. There is only sampling variance.

**Conditions for re-entry.** The LLM substrate may return to the bridge **only** after a closed-loop multi-agent harness with **persistent cross-step state**, **measurable communication graph**, and **memory-depth knob** is committed. At minimum:

- Agents retain and update shared memory across steps (graph or scratchpad).
- At least one tunable parameter maps monotonically to "steps over which a perturbation remains causally active" (e.g. memory-retention window, message-propagation depth, rollout horizon).
- Productivity P is a downstream task metric, not token-count or self-report.

Until then the bridge runs with **three substrates**, not four. Step 9 heterogeneity criterion is evaluated against N = 3.

**Canonical manuscript caveat.** Any Neosynaptex manuscript citing the bridge must state: *"The LLM-agent arm of the bridge is currently null; stateless API-level inference does not instantiate a measurable integration horizon."*

---

## Pre-registration block

| Substrate | Knob(s) | Adapter code location | Pre-registration commit SHA |
|---|---|---|---|
| MFN+ | `alpha` | `substrates/mfn/src/mycelium_fractal_net/core/engine.py` | *(to append in follow-up row-writing PR)* |
| Kuramoto (TradePulse proxy) | `window`, `ema_alpha` | `substrates/kuramoto/analytics/regime/src/core/tradepulse_v21.py` | *(to append)* |
| BN-Syn | `p_conn`, `delay_ms`, `tau_NMDA_ms` | `substrates/bn_syn/src/bnsyn/sim/network.py` | *(to append)* |
| LLM multi-agent | — | scoped out | — |

Follow-up: the bridge adapter module that reads this file, runs the three regimes per substrate, and appends rows to `cross_substrate_horizon_metrics.csv` is **not yet committed**. That is the next artefact.
