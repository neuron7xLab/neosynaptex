# Iteration Loop (Closed-Loop Neuro-AI Update Cycle)

**Status**: Experimental, **default OFF** (no behavior changes unless explicitly enabled).

## Purpose
Provide a minimal, reproducible iteration loop that is prediction-error driven, risk-aware, and auditable without altering existing runtime behavior.

## Phases (contracts)
1. **Propose action** → `ActionProposal` + `PredictionBundle`
2. **Execute** → environment adapter `.step(payload)` → `ObservationBundle`
3. **Prediction error** → `PredictionError` (Δ, |Δ|, clipped Δ)
4. **Update** → bounded parameter update → `UpdateResult` (applied/bounded)
5. **Safety gate** → `SafetyDecision` (allow_next, reason, stability & risk metrics)

Each phase returns typed artifacts in `mlsdm.core.iteration_loop`.

## Data contracts
- `IterationContext`: dt, timestamp, seed, threat (0..1), risk (0..1), regime/mode
- `PredictionBundle` / `ObservationBundle`: predicted vs observed outcomes (vectors)
- `PredictionError`: raw Δ, |Δ|, clipped Δ
- `ActionProposal`: action_id, payload, scores, confidence
- `UpdateResult`: parameter_deltas, bounded, applied
- `SafetyDecision`: allow_next, reason, stability_metrics, risk_metrics, regime

## Regimes & risk coupling
- Regimes: **NORMAL**, **CAUTION**, **DEFENSIVE** (hysteresis + cooldown)
- Threat/risk modulate learning rate (↓ under DEFENSIVE), inhibition gain (↑), and τ smoothing (↑) to damp oscillations.
- Updates are Δ-driven (prediction error), clipped by `delta_max`, learning rate clamped to `[alpha_min, alpha_max]`, parameters clamped to safe bounds, and **stability envelope** checked (max |Δ|, oscillation index, regime-flip rate). Envelope violations force a **fail-safe downgrade** (learning off, DEFENSIVE regime, inference-only).

## Safety gate
- Blocks iteration when |Δ| exceeds bounds or in DEFENSIVE with large residuals.
- Emits per-iteration trace: action, prediction vs observation, Δ metrics, regime, dynamics (α, inhibition, τ, oscillation index, regime-flip rate), update, safety decision.

## Enabling (opt-in)
- Construct `IterationLoop(enabled=True, ...)` and call `step(state, env, ctx)`.
- With `enabled=False` (default), updates are skipped (`applied=False`, `allow_next=True`) to preserve current behavior.

## Tests (behavioral metrics)
- Disabled mode: no updates applied, safety allows progression.
- Δ-learning reduces |Δ| in a deterministic toy environment.
- Threat spikes switch to DEFENSIVE and scale dynamics (α↓, inhibition↑, τ↑).
- Safety gate clamps runaway deltas (bounded=True, allow_next=False).

## Reproducible Iteration Metrics
- Deterministic benchmark: `make iteration-metrics` (writes `artifacts/tmp/iteration-metrics.jsonl`)
- Evidence capture (packs the JSONL automatically): `make evidence`
- Evidence artifact path: `artifacts/evidence/<date>/<sha>/iteration/iteration-metrics.jsonl`

## Environment adapter (toy)
- Protocol: `reset(seed)`, `step(action_payload) -> ObservationBundle`.
- Toy deterministic environment in tests ensures reproducible Δ trajectories.
