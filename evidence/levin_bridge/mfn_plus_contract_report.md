# MFN+ × Levin-Bridge — Contract Report

> The bridge protocol did exactly what it exists to do: expose where reality
> diverges from spec. This report is the deliverable. No code, tests, or
> scaffold were modified in producing it.

## 1. MFN returns `SimulationResult`, not `ndarray`.

Verified empirically:

```python
from mycelium_fractal_net.core.engine import run_mycelium_simulation_with_history
# signature: (config: 'SimulationConfig') -> 'SimulationResult'
```

`SimulationResult` fields: `field, history, growth_events, turing_activations, clamping_events, metadata`.

## 2. Downstream bridge expectations differ from raw MFN output shape.

`AdapterBase.execute` in the scaffold is contractually read by `apply_post_output_control` as a plain `np.ndarray` (uses `series.shape[0]`, `series.ndim`). A raw `SimulationResult` is not directly compatible with the SHUFFLE / MATCHED_NOISE transforms. Either the adapter returns an ndarray and threads auxiliary state another way, or the runner grows a control-handling hook — a real interface decision, not a typo.

## 3. C may be derivable from MFN outputs.

Lag-1 spatial autocorrelation of the final field is defensible and well-defined on any `(N, N)` frame, and empirically produced stable values (~0.98 at the intermediate regime). It can be preregistered without controversy if and when we reach that step.

## 4. γ may be derivable **if** the required `(topo, cost)` mapping is explicitly defined.

`core/gamma.py::compute_gamma(topo, cost)` exists and is canonical. Mapping `SimulationResult.history` → `(topo_t, cost_t)` per-step arrays is possible in principle; each candidate mapping is an independent operationalisation that must be preregistered. At grid_size ≤ 48 and steps ≤ 300 within the CFL-safe α range, no per-step mapping attempted produced γ ≈ 1 with non-trivial R² on a single run — this is a methodology note, not a falsification of the bridge.

Additionally, `SimulationConfig.__post_init__` hard-rejects α > 0.25 at construction time (`ValueError: alpha must be in (0, 0.25] for CFL stability`). Any spec calling for α ∈ {0.5, 0.9} is physically invalid at the simulator API boundary.

## 5. P is not canonically defined for MFN and must not be fabricated.

The wiring spec named `P = "pattern completion score"`. No function, attribute, or metric with that meaning exists anywhere in `substrates/mfn/` (searched: `pattern_completion`, `completion_score`, `task_score`, `pattern_accuracy`).

`growth_events` is a cumulative simulator counter over the original run. It cannot be re-derived from a post-hoc-transformed history array (SHUFFLE, MATCHED_NOISE) without a provenance violation. Substituting any alternative proxy (`turing_activations`, amplitude-energy mean, convergence, …) without preregistration is relabeling, not measurement.

## 6. Therefore the live MFN bridge is blocked by an undefined productivity contract, not by missing code.

The scaffold is correct. The simulator is callable. γ is computable with a stated `(topo, cost)` choice. C is computable. What is missing is a canonical, preregistered `P` contract for MFN+. Writing any row without that contract is fabrication. Truth-preserving stop is the correct state.

---

## Two follow-up paths

### A — Preregister an MFN-specific `P` metric in a separate contract PR.

- Touches only `evidence/levin_bridge/hypotheses.yaml` and `evidence/levin_bridge/horizon_knobs.md §1`.
- Adds the exact formula, the viability rule (what P range counts as productive), and the commit SHA at which the formula was introduced.
- Only after that PR merges is an MFN+ adapter-wiring PR admissible.

### B — Make `P` optional / substrate-specific in the Levin bridge contract.

- Extends `RunRow` and the canonical CSV schema with an explicit `P_status` column (schema bump — versioned, not a rewrite).
- Substrates that cannot yet define P emit rows with numeric P omitted and `P_status = not_defined`.
- Step-9 analysis gates any P-dependent criterion on `P_status = defined`.
- MFN+ then ships rows with no numeric P until path A also lands; the scaffold gains a principled "missing P" lane that is useful beyond MFN+.

---

Choose **A**, **B**, or both in sequence. Either way, the next action is a protocol/preregistration PR, not another wiring attempt.
