# `core.decision_bridge` — invariants contract

This is the human-readable companion to
[`decision_bridge.yaml`](decision_bridge.yaml). Every bullet below
corresponds to one machine-parseable entry in the YAML; CI runs
`tools/audit/decision_bridge_contracts.py` to assert the two stay
in sync.

## Why contracts

The Decision Bridge converges signals from six independent modules
(state-space, resonance map, FDT γ-estimator, online predictor, PI
controller, INV-YV1 diagnosis) into a single verdict used by
downstream execution. An untyped change in any one of them can
silently break an assumption six layers away. A small set of
named, machine-checked invariants replaces the "I think it's
still OK" failure mode with a hard test wall.

## Invariant taxonomy

| Kind | Purpose |
|---|---|
| **safety** | Numeric values stay in their documented domain. A violation is a physical impossibility (gain outside its bounds, probability outside [0,1]). |
| **liveness** | The module makes progress: valid input never causes an exception on the happy path. |
| **integrity** | State is reproducible: same input → same output; idempotent operations do not double-advance. |
| **performance** | Wall-clock budget, bounded above the current measurement by a generous multiplier so only order-of-magnitude regressions fire. |
| **governance** | Classifier / policy invariants that are a design choice, not a physical law. The system could be re-tuned, but inside this contract it is monotone. |

## Registry

### Safety

* **I-DB-2** — `evaluate(non-finite)` always raises. Fail-closed ingress is the core contract; the caller always gets either a valid snapshot or an exception, never a silently corrupted read.
* **I-DB-3** — `critic_gain ∈ [0.01, 1.0]`. The PI controller's gain bounds are part of its declared construction contract.
* **I-DB-4** — `energy_remaining_frac ∈ [0, 1]`. The OEB energy accumulator is clamped to [0, 1]; it can deplete but never overshoot.
* **I-DB-5** — `controller_integral ∈ [-5, 5]` (anti-windup). The integral term is saturated so an adversarial error sequence cannot accumulate unbounded control effort.
* **I-DB-6** — `confidence ∈ [0, 1]`. Confidence is a scaled count of observed ticks.

### Liveness

* **I-DB-1** — `evaluate(valid input)` never raises. Exhaustively checked with property-based tests across arbitrary finite histories.

### Integrity

* **I-DB-12** — Idempotence per tick. Calling `evaluate(tick=t)` twice returns the memoised snapshot (same object identity) and advances neither the controller nor the energy accumulator. This is what makes the bridge safe for multi-observer use.
* **I-DB-15** — `SensorGate.sanitize` is idempotent. Feeding the output of `sanitize` back in must produce a zero-clip report and a bit-identical array. Without this, the audit trail would shift under replay.
* **I-DB-L1** — `TelemetryLedger.verify` detects tamper. The ledger is append-only with SHA-256 Merkle-chained self-hashes; any single-byte change, mid-stream deletion, or fabricated tail event breaks the chain.

### Performance

* **I-DB-P1** — `evaluate(history_n=20)` p95 latency < 15 ms. The budget is ≈ 10× above current measurement on a CI-class single-thread runner. Memoised re-evaluation is required to be at least 5× faster than a cold call.

### Governance

* **I-DB-H1** — Health classifier is monotone under dominance. For any two signal sets `s'` and `s`, if `s'` is at least as good as `s` on every axis (diagnosis, regime, hallucination risk, stability, `|γ − 1|`), then `rank(health(s')) ≥ rank(health(s))`. Exhaustively enumerated over the discrete axes (≈ 262 144 pairs).

## Adding a new invariant

1. Pick an unused identifier in the `I-DB-*` / `I-DB-H*` / `I-DB-L*` / `I-DB-P*` namespace.
2. Add the entry to [`decision_bridge.yaml`](decision_bridge.yaml) including `enforced_by` paths to real tests.
3. Update this document with a one-line rationale in the matching kind section.
4. Run `python -m tools.audit.decision_bridge_contracts` locally — it is zero-exit if YAML and tests agree.
5. The CI gate will block the PR otherwise.

## Removing an invariant

Invariants only leave the registry with an ADR. See
[`docs/adr/`](../adr/) for the template.
