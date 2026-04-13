# MFN+ Productivity (P) Preregistration — Levin Bridge Contract v2

**Status.** `p_status: not_defined`. Written to `evidence/levin_bridge/hypotheses.yaml` under `variables.P.current_preregistrations.mfn_plus`.

**Decision standard applied.** "Prefer leaving P undefined over defining a weak or semantically inflated metric."

**This document is a semantic preregistration, not a live wiring specification.** No adapter code, no schema change, no live run is produced by this PR.

---

## 1. The honest summary

MFN+ is a **morphogenesis simulator**, not a task-solver. `SimulationResult` (`substrates/mfn/src/mycelium_fractal_net/core/types.py`) carries only dynamics/activity fields:

| Field | What it is | Is it productivity? |
|---|---|---|
| `field` | Final 2D potential field `(N, N)` | No — terminal state. |
| `history` | Full trajectory `(T, N, N)` | No — dynamics record. |
| `growth_events` | Count of growth activations | No — activity counter. |
| `turing_activations` | Count of Turing-pattern activations | No — activity counter. |
| `clamping_events` | Count of stability-guard clampings | No — stability-guard counter. |
| `metadata` | `SimulationMetrics` dict of field statistics | No — diagnostic features. |

Calling any of these "productivity" is relabeling. The contract-v2 split was introduced specifically to prevent that.

## 2. Higher-level task frames that do exist in the codebase

MFN+ exposes two higher-level modules that _do_ frame tasks with accuracy-like outputs. Each requires a substrate-owner decision that has **not been made**:

### 2.1 `mycelium_fractal_net.bio.persuasion.FieldActiveInference`

- **What it is.** Friston-Levin active inference. Computes variational free energy of a field state relative to a **target morphology**. Returns `FreeEnergyResult.accuracy`, decomposed as `-likelihood_precision × MSE(obs, target)`.
- **Task framing.** "How close is the evolved field to a preregistered target?"
- **Candidate P.** `accuracy` (or `-free_energy`).
- **Unresolved decision.** Which target morphology is canonical for the Levin bridge? The repo has no default target. Picking one is a modeler choice that would become a hidden parameter unless explicitly canonized.

### 2.2 `mycelium_fractal_net.core.forecast.forecast_regime(sequence, horizon)`

- **What it is.** Split `sequence` into prefix and suffix; fit an internal model on prefix; predict suffix. Returns `ForecastResult.evaluation_metrics` with RMSE-like keys.
- **Task framing.** "Can the system predict its own near-future state?"
- **Candidate P.** `1 − RMSE(predicted, actual) / RMSE_baseline` or `evaluation_metrics["r2"]` when present.
- **Unresolved decision.** For post-output controls — SHUFFLE and MATCHED_NOISE — the "history" passed through the pipeline is a transformed artefact, not a real trajectory. Forecasting on a time-shuffled or noise-replaced history is definitionally meaningless. The contract has no rule for how productivity should be reported on a post-hoc-transformed control; either forecasting is declared inapplicable for those rows (and P is emitted only for PRODUCTIVE / OVERCOUPLED / UNDERCOUPLED), or a substrate-specific rule is preregistered. Neither decision has been made.

## 3. Three candidate options evaluated and rejected at this commit

### Option α — target-anchored active inference

Preregister a fixed target field `T*` (e.g. the equilibrium state of an MFN+ run at default parameters from a frozen seed). Define:

> `P := -FieldActiveInference(target=T*).compute_free_energy(result.field).free_energy`

**Why it is operationally viable.** The metric is substrate-native, already implemented, has a clear semantic ("closer to target → higher P"), and survives PRODUCTIVE / OVERCOUPLED / UNDERCOUPLED controls. Post-output controls can be declared inapplicable with documentation.

**Why it is not adopted now.** Choosing `T*` is a first-order canonical decision that deserves its own preregistration PR. Different targets will produce different P orderings across regimes. Quietly picking a target inside a wiring PR is exactly the hidden-parameter failure mode Section 5.2 of `docs/ADVERSARIAL_CONTROLS.md` forbids.

### Option β — forecasting accuracy

Define:

> `P := 1 − RMSE(forecast_regime(history[:k], horizon=h).predicted_states, history[k:k+h]) / RMSE_baseline`

for preregistered `k`, `h`, and baseline.

**Why it is operationally viable.** Genuine task framing ("the system can predict itself"). Uses an existing API. Preregistrable split ratio.

**Why it is not adopted now.** Incompatible with SHUFFLE / MATCHED_NOISE post-output controls by construction — forecasting on transformed history is meaningless. The contract would need an explicit rule that post-output-control rows are emitted with `P_status = not_defined` and separately, PRODUCTIVE / OVERCOUPLED / UNDERCOUPLED rows are emitted with `P_status = defined`. That is a **mixed-P-status-per-cell** extension not currently specified in the contract v2 document. Adding it is a separate PR.

### Option γ — cross-seed reproducibility as 1 / Var(summary)

Run K seeds per cell; define `P := 1 / Var(growth_events)` or similar across seeds.

**Why it is not adopted.** Reproducibility is stability, not productivity. Re-labelling it as P would conflate what the bridge protocol tries to separate (Section 4.3 of `docs/ADVERSARIAL_CONTROLS.md` — parameter-sweep robustness is a control-class property, not a productivity metric). Distinct concept, wrong slot.

## 4. What this commit changes

- `evidence/levin_bridge/hypotheses.yaml` — adds `current_preregistrations.mfn_plus` with `p_status: not_defined`, explicit `blocking_reason`, explicit `required_future_decision`, and the list of candidates evaluated and rejected.
- This companion note at `docs/protocols/mfn_plus_productivity_prereg.md`.

## 5. What this commit does NOT change

- No schema.
- No bridge code.
- No adapter wiring.
- No H / C / γ derivation.
- No tests, except minimal fixture extension if required for YAML validation.
- No canon (`CANONICAL_POSITION.md`, `docs/protocols/levin_bridge_protocol.md`, `docs/ADVERSARIAL_CONTROLS.md`, `controls.yaml`, `horizon_knobs.md`) — untouched.

## 6. Unblock path

A future substrate-owner PR must pick exactly one of Options α / β (Option γ is rejected as conceptually miscategorised) and commit:

- The exact formula.
- The exact preregistered constants (target field SHA for α; split ratio and baseline for β).
- For Option β specifically: an extension to the contract that permits mixed `P_status` across control families within a single cell, OR a rule that only the productive / overcoupled / undercoupled rows carry `P_status = defined`.
- The commit SHA at which the formula was introduced (to be filed per `evidence/PREREG.md` conventions).

Only after that PR lands may an MFN+ adapter emit rows with `P_status = defined`. Until then, any MFN+ row that enters `cross_substrate_horizon_metrics.csv` must carry `P_status = not_defined` or `preregistered_pending` with `P` left empty. This is enforced by `RunRow.__post_init__` in `substrates/bridge/levin_runner.py`.

## 7. Why this is the correct result

Both Alternative A (define one) and Alternative B (remain undefined) were admissible outcomes at PR start. The empirical answer — MFN+ has no canonically defensible productivity metric yet — is Alternative B. Recording that truth is a **positive result**, not a failure: it converts a hidden semantic ambiguity into an explicit, auditable, version-controlled blocker. Future work is now required to either resolve α / β with a dedicated PR or ship MFN+ bridge rows in the `p_status = not_defined` lane that contract v2 was designed to support.
