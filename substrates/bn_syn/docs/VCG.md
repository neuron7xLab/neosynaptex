# /docs/VCG.md
## Verified Contribution Gating (VCG) — Result-Based Social Verification Module

**Status**: Optional governance extension (non-core).  
**Normativity**: Normative for VCG behavior if enabled; VCG does not alter the 12-core neurodynamics components.

### 1) Purpose
VCG reduces **parasitic strategies** (pattern-matching interaction without measurable contribution) by applying a *symmetric, outcome-based* policy:
- If an agent's observable contribution is consistently below threshold, the system mirrors that outcome by withdrawing future **social/resource support** (routing priority, compute budget, access).

This is **not** framed as “punishment”; it is a deterministic resource-allocation rule.

### 2) Scientific foundation (Tier-A)
VCG is grounded in peer-reviewed reciprocity and cooperation mechanisms:
- [NORMATIVE][CLM-0015] **Reciprocal altruism / contingent reciprocity** (Trivers 1971, DOI:10.1086/406755) — outcome-contingent cooperation.  
- [NORMATIVE][CLM-0016] **Tit-for-tat stability in repeated interactions** (Axelrod & Hamilton 1981, DOI:10.1126/science.7466396).  
- [NORMATIVE][CLM-0017] **Reputation / indirect reciprocity via public outcome signals** (Nowak & Sigmund 1998, DOI:10.1038/31225).  
- [NORMATIVE][CLM-0018] **Defector suppression via costly sanctioning** (Fehr & Gächter 2002, DOI:10.1038/415137a).

### 3) Inputs and observable metrics (SSOT)
VCG operates on **observable outcomes** (no mind-reading, no intent inference).

Let an agent be indexed by *i* and an evaluation window be *W* discrete steps.

**Contribution score**:
- Define task-specific measurable output: `contrib_i(t)` (e.g., validated PR merged, passed tests, accepted patches, verified dataset improvements).
- Define effort proxy (optional, non-normative): `cost_i(t)` (e.g., CPU seconds, tokens, wall-time).

Compute rolling aggregates:
- `C_i = Σ_{t∈W} contrib_i(t)`
- `K_i = Σ_{t∈W} cost_i(t)` (optional)

**Support level**:
- `S_i ∈ [0, 1]` (routing priority / resource multiplier)

### 4) Deterministic gating rule (contract)
Parameters: `θ_C` (minimum contribution), `α_down` (decrease rate), `α_up` (recovery rate), `ε` (stability floor).

1. **Update** (per window):
   - If `C_i < θ_C` then `S_i ← max(0, S_i - α_down)`
   - Else `S_i ← min(1, S_i + α_up)`
2. **Routing & budget application**:
   - Effective allocation multiplier: `alloc_i = ε + (1-ε)·S_i`
   - Apply to: queue priority, parallelism limit, retries, or compute credits.

**Hard invariants**:
- I1: `S_i` is deterministic given the same observable log + parameters.
- I2: `S_i` is monotonic non-increasing while `C_i < θ_C` persists.
- I3: Recovery is possible (no permanent exclusion) if `C_i ≥ θ_C`.
- I4: Proven invariants apply to the pure VCG function only; no claim is made about integration with simulation-core neuron/synapse state.

### 5) Failure envelopes & mitigations
- **False-negative contribution** (measurement misses real value) → require *verifiable* contribution signals; keep `α_down` conservative.
- **Goodharting** (gaming the metric) → use multi-signal contribution, audit sampling, and per-task validators.
- **Cold start disadvantage** → set initial `S_i = 1` and apply a grace period `W_grace`.
- **Collusion / reputation manipulation** → use signed logs, reviewer diversity constraints, and anomaly detection (non-core).

### 6) Acceptance criteria (VCG-enabled)
- A1: Replaying the same event log yields identical `S_i(t)` traces (bitwise).
- A2: An agent with `C_i < θ_C` for `k` consecutive windows shows strictly decreasing `S_i` until floor.
- A3: An agent regains `S_i → 1` after sustained `C_i ≥ θ_C`.
- A4: Acceptance proofs cover the pure VCG function only; no verified simulation-core integration is asserted.

### 7) Claim mapping
Normative claims in this module map to:
- CLM-0015, CLM-0016, CLM-0017, CLM-0018 (see `bibliography/mapping.yml`).
