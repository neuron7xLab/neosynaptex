# MFN+ × Levin-Bridge — First-Contact Contract Report

**Status.** Truth-preserving stop before any live CSV write.
**No rows have been written.** No code has been merged that fabricates, relabels, or substitutes the canonical metrics.

**Branch state at time of stop.** Repository is back at `main`. All 22 existing bridge tests remain green.

---

## 1. What the contract actually is vs. what the scaffold assumed

### 1.1 MFN+ returns `SimulationResult`, not `ndarray`

Verified empirically:

```python
from mycelium_fractal_net.core.engine import run_mycelium_simulation_with_history
import inspect
inspect.signature(run_mycelium_simulation_with_history)
# → (config: 'SimulationConfig') -> 'SimulationResult'
```

`SimulationResult` fields (`dataclasses.fields`):

```
field, history, growth_events, turing_activations, clamping_events, metadata
```

- `field` — final frame `(N, N)`.
- `history` — full trajectory `(T, N, N)`.
- `growth_events, turing_activations, clamping_events` — scalar counters over the run.
- `metadata` — nested dict including `config` snapshot and `SimulationMetrics`.

The bridge `AdapterBase.execute` scaffold expects `np.ndarray` because `apply_post_output_control` (shuffle / matched-noise) operates on `series.shape[0]` and `series.ndim`. Passing a `SimulationResult` directly causes `AttributeError` on the post-output-control path. This is a **real type-contract mismatch** between the bridge and the MFN+ return surface.

### 1.2 `alpha` CFL validation (confirmed hard constraint)

`SimulationConfig(alpha=a)` raises `ValueError("alpha must be in (0, 0.25] for CFL stability")` at `__post_init__` for any `a > 0.25`.

Empirically: 0.05 / 0.1 / 0.18 / 0.24 / 0.25 accepted; 0.26 / 0.5 / 0.9 rejected.

The bridge's canon values in `evidence/levin_bridge/horizon_knobs.md` (0.08 / 0.18 / 0.24) are all CFL-safe. Any specification calling for `α ∈ {0.5, 0.9}` cannot be executed and is physically invalid at the simulator API boundary.

---

## 2. Per-bridge-field derivability from `SimulationResult`

### 2.1 `H = alpha` — **derivable**

Trivially: the value passed into `SimulationConfig`. Must be threaded from the adapter instance to `compute_metrics` (since `compute_metrics` sees transformed output, not config). Cleanly solvable via adapter instance state.

### 2.2 `gamma` — **derivable, with documented caveats**

`core/gamma.py::compute_gamma(topo, cost) -> GammaResult` exists and is canonical. Call signature is confirmed.

Operationalisation attempts made during exploration (none committed, all scratch):

| Attempt | Per-step `topo` | Per-step `cost` | Log-range on intermediate α | Verdict |
|---|---|---|---|---|
| A | `Σ \|∇field\|` | `Σ field²` | topo 0.41 | `INSUFFICIENT_RANGE` |
| B | Betti-0 (connected components above μ+0.5σ) | `Σ field²` | topo 2.9, cost 0.5 | `LOW_R2` (R² ≈ 0) |
| C | spatial entropy | `Σ field²` | 0 | `INSUFFICIENT_DATA` |
| D | total field mass | `1/entropy` | 0.2 | `INSUFFICIENT_RANGE` |
| E | A, over full transient (t ≥ 1) | A, over full transient | α=0.24 only: γ=−0.69, R²=0.73, COLLAPSE | valid but negative |

**Empirical finding.** At grid_size ≤ 48, steps ≤ 300, within the CFL-safe α range, the MFN+ simulator reaches quasi-equilibrium with **insufficient log-range per single run** to support Theil-Sen γ estimation at compressed and intermediate regimes. Only the expanded regime (α = 0.24) produced a non-NaN γ, and that γ was **negative** with verdict `COLLAPSE` — well outside the γ ≈ 1 canon.

This is **not evidence against the γ ≈ 1 claim**; it is evidence that the **single-run per-cell γ extraction contract is methodologically ill-posed for MFN+ at these scales**. The canonical γ-on-MFN+ in the repo (`substrates/mfn/scripts/g4_gamma_scaling.py`, `substrates/gray_scott/adapter.py`) achieves γ ≈ 1 via **cross-parameter ensemble fits**, not within a single trajectory.

### 2.3 `C` — **derivable (first-pass)**

Lag-1 spatial autocorrelation of the final field is a defensible C for a reaction-diffusion system and produced reasonable values (~0.98 at intermediate α). This metric can be preregistered without controversy.

### 2.4 `P` — **NOT canonically defined**

This is the core blocker.

- The bridge protocol's `horizon_knobs.md §1` wrote `P = SimulationResult.growth_events`. That was a DRAFT operationalisation, not an audited preregistration.
- The wiring task spec instead specified `P = "pattern completion score"`, which **does not exist as a function, attribute, or metric anywhere in `substrates/mfn/`**. Searched: `pattern_completion`, `completion_score`, `task_score`, `pattern_accuracy` — zero matches.
- `growth_events` is a cumulative simulator counter over the ORIGINAL run. It **cannot be re-derived from a post-hoc-transformed history array** (e.g. after SHUFFLE or MATCHED_NOISE). Using the ORIGINAL counter for a transformed-output row is a provenance violation.
- Replacing it with `np.mean(history ** 2)` (amplitude-energy proxy) is **relabeling, not re-derivation**. It changes the semantics of P without preregistration and is forbidden by the stop order.

**Conclusion.** There is no metric currently in the MFN+ public surface that (a) corresponds to task-level productivity in the bridge's sense and (b) remains well-defined under the post-output control transforms. Writing any row with any candidate `P` at this time is fabrication.

---

## 3. Invariants preserved

- No row has been appended to `evidence/levin_bridge/cross_substrate_horizon_metrics.csv`.
- `substrates/bridge/levin_runner.py` unchanged from merged state (PR #67).
- `tests/levin_bridge/test_levin_runner.py` unchanged; all 22 assertions pass.
- No live adapter registered. `ADAPTERS` tuple still contains scaffold-only classes that raise `NotImplementedError`.
- LLM substrate guard (`test_llm_substrate_not_present`) unchanged.

---

## 4. Proposed follow-up PR scope (two alternatives; pick one)

### Alternative A — Preregister an MFN-specific `P`

Define a P that is:

1. Computable from a `(T, N, N)` history array alone (so it survives post-output transforms with documented semantics).
2. Preregistered as a specific formula in a signed PREREG block in `hypotheses.yaml`, with the `commit_sha` at which the formula was introduced.
3. Has a viability rule (e.g. "P > threshold" required for the row to enter pooled analysis, else row is filed under `non_productive`).

Candidate formula (NOT adopted, for discussion only):

> P_mfn := fraction of time steps in which `(Σ |∇field_t| / Σ |field_t|)` exceeds the median value of the same ratio across the run's quiescent prefix.

This measures "fraction of run spent in an organised-pattern regime" and is well-defined for any 3D array. But it is NOT currently endorsed; it is an example of what a preregistered formula would look like.

Action items if Alternative A is chosen:
- Open a PREREG PR that touches only `hypotheses.yaml` and `horizon_knobs.md §1`, adding the exact formula with its rationale.
- Only AFTER that PR merges, open the adapter-wiring PR that computes the newly-canonical P.

### Alternative B — Make `P` optional / substrate-specific in the bridge contract

Relax the bridge contract so `P` becomes either:

- Nullable for substrates that cannot yet define it (recorded as `""` or `P_status=not_defined` in the row), OR
- A substrate-defined field whose semantics are stored in a parallel `evidence/levin_bridge/p_definitions.yaml` keyed by substrate.

In this path, MFN+ rows would ship with `P` empty and a corresponding `P_status` marker. The pooled analysis at Step 9 would exclude MFN+ from any P-gated viability check until a preregistered P is added.

Action items if Alternative B is chosen:
- Open a schema PR that extends `RunRow` and `cross_substrate_horizon_metrics.csv` with a `P_status` column (schema bump — explicit, versioned).
- Add a test verifying that every row either has a numeric `P` or a recognised `P_status` value.
- Only after that schema PR merges, open the adapter-wiring PR that ships MFN+ rows with `P` omitted and `P_status = not_defined`.

### Alternative C (also on the table, explicit) — Cross-parameter ensemble wiring

Abandon the "one simulation per cell" design for MFN+. Each cell becomes a K-run mini-sweep over α in a narrow neighbourhood (or over another Turing parameter), and γ is fit across the K endpoints — matching the `gray_scott/adapter.py` pattern that actually achieves γ ≈ 1 in the repo. This resolves both the γ log-range issue **and** gives P per-cell as ensemble-mean `growth_events` (since all K runs are native simulations, not post-hoc transforms).

Action items if Alternative C is chosen:
- Open a protocol amendment PR explicitly changing the bridge's per-cell contract from "one run" to "K-run ensemble" and preregistering K, the α-neighbourhood width, and the P aggregation rule.
- Then wire MFN+ and verify.

---

## 5. Recommendation

Prefer **Alternative C** on empirical grounds: the cross-parameter ensemble is the only design where both γ and P are derivable without relabeling, and it mirrors the methodology that actually produced γ ≈ 1 on reaction-diffusion substrates elsewhere in the repo. Alternatives A and B are acceptable but leave the core γ log-range issue unresolved.

Whichever alternative is chosen, the next action is a **protocol/preregistration PR**, not another wiring attempt. Wiring without a preregistered P contract is how fabrication creeps in.

---

## 6. What did NOT happen (explicit)

- No `substrates/bridge/adapters/` directory exists on any branch.
- No row exists in `cross_substrate_horizon_metrics.csv` beyond the schema header.
- No test was weakened or replaced.
- `MFNPlusAdapter.execute` still raises `NotImplementedError`, per scaffold.
- `CANONICAL_POSITION.md`, `hypotheses.yaml`, `controls.yaml`, `horizon_knobs.md`, `levin_bridge_protocol.md` — all untouched by this stop.

Truth-preserving stop complete. Awaiting alternative selection before any further wiring.
