# Phase 4a: Horizon Trace Protocol

**Status:** frozen prose. Content changes require a protocol-version bump.
**Authoritative contract:** `substrates/serotonergic_kuramoto/horizon_trace_contract.yaml`.
**Authoritative lint:** `tools/audit/horizon_trace_lint.py`.
**Authoritative test:** `tests/test_phase_4a_horizon_trace_contract.py`.
**Scope:** `serotonergic_kuramoto`. Other substrates in scope of future
Phase 4a contracts.

## 1. First Principle

The substrate core is not directly admissible evidence.
Only its boundary trace is admissible.

A boundary trace is:

* emitted by code (declared in a known source file at a known symbol),
* reproducible (deterministic given seed and adapter version),
* hash-bound (recomputable to the same SHA-256 from disk-resident
  adapter source + declared parameters),
* interpretable (its physical or dynamical meaning is declared in this
  protocol, not inferred from intent),
* null-testable (its expected behaviour under registered null families
  is declared up-front),
* estimator-compatible (the estimator that consumes it is named and
  bound in `tools/phase_3/admissibility/`),
* falsifiable (a measurable failure mode would invalidate it).

Anything inside the simulation that is not exposed through such a
trace is not evidence — even if a human can read its values out of
the running process. **A debug print is not a contract.**

## 2. Anti-Cartesian Rule

Reject — globally and at PR-time — claims of the form:

> "The system contains γ ≈ 1 internally."

That sentence is the failure mode this entire protocol exists to
prevent. It is the structurally-Cartesian assertion that an internal
state can ground an external claim — that the brain in the vat
contains the truth, that the simulation has a "true γ" hidden inside,
and that all we need is to reach in and grab it.

Accept — only under all of the following conditions, jointly — claims
of the form:

> "The boundary trace of `serotonergic_kuramoto` preserves a scaling
> relation γ̂ at exponent X with CI [Y, Z], under canonical observable
> definitions D, canonical coordinate C, integration parameters I,
> ensemble size E, registered null families F (Bonferroni α/k), with
> result_hash H and estimator E_id at admissibility floor N_min."

That sentence has 11 declared variables. None of them is "γ ≈ 1".
Whatever number actually appears in `γ̂` is the answer; the protocol
does not pre-shape it.

## 3. Current Trigger

Phase 4a was opened because three independent runs over the *same*
substrate produced three different γ̂ values, where the differences
are far larger than the precision floor of any single estimator:

| run | sweep | N | estimator | γ̂_obs |
|---|---|---:|---|---:|
| v1 ledger | linear C | 20 | sorted-OLS | **1.0677** |
| v2 patch (sorted-OLS) | log-uniform C (geomspace) | 128 | sorted-OLS | **0.7403** |
| v2 patch (Theil–Sen) | log-uniform C (geomspace) | 128 | canonical Theil–Sen | **0.0661** |

A single estimator change moves γ̂ by a factor of ~16. A single sweep
change moves γ̂ by ~30 %. These are not small fluctuations.

**Forbidden interpretation:** "the hypothesis is dead." That sentence
asserts that the falsifier won. But the conditions of falsification
were never met cleanly — different (estimator, coordinate, sweep)
combinations are different *measurements*, not different verdicts on
one measurement.

**Allowed interpretation:** "the boundary observable and coordinate
system are not yet admissible enough to support a single γ claim."
This sentence is what Phase 4a declares.

## 4. Horizon Observables

Every observable currently consumed by the Phase 3 null-screen runner
through `serotonergic_kuramoto` is audited below.

The phase 3 runner's substrate-loader for this substrate
(`tools/phase_3/run_null_screen.py::_load_serotonergic_kuramoto`)
reaches into `adapter._samples` — a private attribute of the adapter
class — to extract `topo` and `thermo_cost` arrays. The contract
declares this private-API exposure explicitly as a Phase 4 risk: the
boundary is not currently a public method, it is a private dict.

For each observable, see the canonical entry in
`horizon_trace_contract.yaml`. Summary table:

| name | source | code symbol | status |
|---|---|---|---|
| `topo` | `substrates/serotonergic_kuramoto/adapter.py` | `SerotonergicKuramotoAdapter.topo` (and the `topo` key in the private `_samples` dicts) | UNDER_DEFINED_TRACE |
| `thermo_cost` | `substrates/serotonergic_kuramoto/adapter.py` | `SerotonergicKuramotoAdapter.thermo_cost` (and the `thermo_cost` key in `_samples`) | UNDER_DEFINED_TRACE |

Every other key in `_samples` (`R`, `K_eff`, `K_over_Kc`, `R_std`,
`phase_entropy`, `mean_plv`, `c`) is **internal-only**, not exposed
through a DomainAdapter-Protocol method, and therefore — under this
contract — INTERNAL_ONLY_NOT_EVIDENCE until promoted by an explicit
contract update.

### `topo` — UNDER_DEFINED_TRACE

* **Definition (literal, code-grounded):** count of pairs `(i < j)`
  with `|sin(θ_i − θ_j)| > 0.3` at the *single end-of-window* phase
  snapshot, IC-averaged over `N_IC = 4` parallel trajectories. Read
  via `adapter.topo()` with a 2 % multiplicative jitter applied per
  read.
* **Units / scale:** integer count in `[0, N(N−1)/2] = [0, 2016]` for
  `N = 64`. Not normalised. Read-time jitter (1 ± 0.02) breaks the
  integer domain after the boundary.
* **Why UNDER_DEFINED_TRACE:**
  - the threshold 0.3 has no theoretical justification — neither the
    code nor the docstring nor the traceability matrix in
    `docs/traceability/kuramoto_traceability_matrix.md` cites a
    paper, an analytic expectation, or a bound;
  - the metric is a single-time snapshot, not a time-averaged
    invariant; it has no stationarity check;
  - the name "topo" implies topology (homotopy / persistent homology)
    but the implementation is a pair counter with no topological
    structure;
  - cross-substrate normalisation is undefined.
* **Falsifiers (declared in the YAML contract):** synthesised IID
  phases vs IAAFT-of-real surrogate distinguishability test;
  half-window stationarity test; threshold-sweep parametric
  sensitivity test.

### `thermo_cost` — UNDER_DEFINED_TRACE

* **Definition (literal):** time-average over the 10 000-step
  measurement window of `Σ_i |K_eff · R(t) · sin(ψ(t) − θ_i(t))|`,
  IC-averaged. Read via `adapter.thermo_cost()` with 2 % jitter.
* **Units / scale:** `rad/s × oscillator-count`, time-averaged. Scales
  trivially with `K_eff` by construction.
* **Why UNDER_DEFINED_TRACE:**
  - the L1 norm `|·|` choice is unjustified; mean-field "work" is
    canonically L2 (energy-like) or signed sum;
  - the name "thermo_cost" implies a thermodynamic quantity but no
    `kT`, no entropy, and no fluctuation-dissipation linkage is
    declared;
  - the linear `K_eff` factor entangles the modulation knob with the
    underlying physics — a measurement against c is necessarily
    confounded with the knob unless `K_eff` is divided out;
  - only the mean is reported; variance is discarded, making
    fluctuation-channel analysis impossible.
* **Falsifiers:** held-K_eff-vary-c null; random-pairing coupling
  null; first-half vs second-half window stationarity test.

## 5. Horizon Coordinate Audit

### Raw `c` — SUSPECT

`c ∈ [0, 1]` is the 5-HT2A pharmacological-modulation knob. The
adapter implements a deterministic linear mapping
`K_eff(c) = K_base · (1 − 0.7·c)`. With `K_base = 2.0` and
`σ_op = 0.065 Hz` (so `K_c = σ_rad · sqrt(8/π) ≈ 0.6517 rad/s`), the
phase transition `K_eff = K_c` is reached at:

```
2.0 · (1 − 0.7·c) = 0.6517
1 − 0.7·c        = 0.32585
c                = (1 − 0.32585) / 0.7
                 ≈ 0.963
```

The adapter docstring (line 43) claims the crossing is at `c ≈ 0.71`.
**The docstring contradicts its own constants.** This is itself
evidence that `c` has not been audited as a physical coordinate — the
docstring's own author did not verify the crossing point.

* **Status:** SUSPECT — may be an implementation knob, not a critical
  coordinate.
* **Required tests** (from contract):
  1. dual-fit `log(observable) ~ log(c)` and `log(observable) ~ log(|r|)`
     on the same trajectory; compare R² and slope CI;
  2. regime split — verify a single γ does not fit both `r > 0` and
     `r < 0`;
  3. constant-K_eff varying-c null — if any observable still scales
     with c, c is a confound;
  4. fix the docstring crossing claim.

### Critical distance `r = (K_eff − K_c) / K_c` — CANDIDATE_UNDEFINED

Kuramoto theory predicts power-law scaling against `r`, not `c`:

* `R ~ r^(1/2)` for `r > 0` (mean-field super-critical),
* `R ~ 1/√N` for `r < 0` (incoherent / sub-critical),
* `χ ≡ N · var(R) ~ |r|^(-1)` near `r = 0`.

The components `K_eff` and `K_c` are both deterministic given the
adapter's seed and the (Gaussian-quantile) frequency bank, so `r` is
well-defined inside this simulation. But:

* **for the simulation:** `K_c = σ_rad · sqrt(8/π)` is a closed-form
  mean-field formula valid for Lorentzian or Gaussian frequency
  distributions; the adapter uses Gaussian quantile draws, so the
  formula applies — but this assumption must be declared explicitly,
  not silent in a docstring;
* **for any future real substrate:** an *empirical* `K_c` estimator
  with a CI is required, not a literal closed-form import;
* **regime contracts:** the canonical exponent is regime-specific —
  one fit cannot span `r > 0` and `r < 0` and one cannot include
  `r = 0` directly.

### Verdict table

| coordinate | verdict |
|---|---|
| `raw_c` | SUSPECT |
| `critical_distance` | CANDIDATE_UNDEFINED |

Phase 4a does **not** implement `K_eff` or `K_c` as boundary values
beyond their adapter-internal use. Phase 4b is the PR that promotes
`r` to a boundary observable, after the contract is updated.

## 6. Interface Invariants

Every claim that "γ̂ on `serotonergic_kuramoto` is X with CI [Y, Z]"
must hold these invariants stable from the moment of measurement to
the moment of report:

| invariant | reason | where enforced | current status | missing enforcement |
|---|---|---|---|---|
| observable definition | a γ on different observables is a different number | YAML contract `observables.*` | declared in 4a | CI gate that diff-fails when adapter.py changes an observable without contract update |
| coordinate definition | a γ on different coordinates is a different number | YAML contract `coordinates.*` | declared SUSPECT/CANDIDATE_UNDEFINED in 4a | Phase 4b PR selects one canonical coordinate |
| simulation seed path | reproducibility | adapter constructor `np.random.default_rng(seed)` | enforced; tested in Phase 3 | per-c stationarity rejection not part of seed contract |
| burn-in rule | windowed observables require steady-state | `_BURN_IN_STEPS = 2000` constant | declared, ≈ 1.30 · τ_relax(K_c), too short | adaptive burn-in tied to τ_relax(K_eff) at each c |
| integration length | ergodicity | `_STEPS_PER_WINDOW = 10000` constant | declared, marginal | adaptive window length tied to convergence test |
| ensemble size | variance estimation | `_N_IC = 4` constant | severely undersampled (SE on R ≈ 0.25) | enforce N_IC ≥ 32 near criticality |
| estimator identity | γ̂ is estimator-relative | `tools/phase_3/admissibility/verdict.py` (`ADMISSIBLE_AT_N_MIN_128`) | enforced for null-screen runner | substrate adapters do not declare their intended estimator |
| null family list | structural falsification | `tools/phase_3/family_router.py` | enforced (Bonferroni α/3 for kuramoto_iaaft + linear_matched + iaaft_surrogate) | a stationarity-preserving null targeting boundary trace integrity (Phase 4c) |
| result_hash | byte-identical reproducibility | `tools/phase_3/result_hash.py` | enforced; tested | substrate-side observable-definition hash not yet bound |
| ledger proposal boundary | no auto-promotion | verbatim `"PROPOSAL ONLY — Phase 3 never auto-promotes."` in `tools/phase_3/run_null_screen.py:662`; `CANON_VALIDATED_FROZEN` global | enforced; `FROZEN_LADDER_STATES` rejects VALIDATED globally | none at PR-level; intent of future maintainers is the only un-enforced channel |

## 7. Failure Modes

Concrete ways the system can fake γ ≈ 1, with detection and target
phase. The full machine-readable list is in
`horizon_trace_contract.yaml::failure_modes`.

| failure mode | detection | required test | Phase target |
|---|---|---|---|
| linear sweep overweighting one regime | `γ̂` stability across {linspace, geomspace, uniform-in-r} | per-coordinate sensitivity matrix | 4b |
| low N trajectory | admissibility verdict on N | enforce `N ≥ MIN_TRAJECTORY_LENGTH` at adapter level | 4c |
| sorted-OLS artefact | compare canonical Theil–Sen vs sorted-OLS γ̂ on identical data | deprecate sorted-OLS or restrict to within-regime | 4d |
| non-stationary transient | split-window mean comparison at near-critical c | stationarity check inside `_simulate_at_concentration`; emit `INCONCLUSIVE` on fail | 4c |
| insufficient burn-in | run `2000` and `20000` burn-in steps; compare end-of-window observables | adaptive burn-in tied to `τ_relax(K_eff)` | 4c |
| too few initial conditions | bootstrap over IC bank; report SE per observable | enforce `N_IC ≥ 32`; document SE at every c | 4c |
| wrong control variable | dual-fit `c` vs `r`; compare R² | declared in `coordinates.required_tests` | 4b |
| observable not physically meaningful | each observable has no theoretical scaling expectation declared | declared `observables.boundary_meaning` (currently `TODO_OR_FOUND`) | **4a** (this PR) |
| estimator–coordinate mismatch | `result_hash` diverges across `(estimator × coordinate × sweep)` on identical adapter | explicit sensitivity matrix | 4b + 4d |
| null family preserving wrong structure | per-family null distribution shape on a fixed trajectory | per-family audit on synthesised pairs | 4d |

## 8. Phase Split

Phase 4 is a substrate-science rebuild, not a patch series.

| phase | scope | preconditions | output |
|---|---|---|---|
| **4a** (this PR) | horizon trace contract; declarative; YAML + lint + tests + protocol; no simulation change; no estimator change; no observable redefinition | none | machine-readable contract + protocol doc + lint + 10 contract tests; observables flagged UNDER_DEFINED_TRACE; `boundary_meaning` and `expected_null_behavior` left as `TODO_OR_FOUND` for future deliverables to fill |
| **4b** | coordinate rebuild — promote `r = (K_eff − K_c)/K_c` to a boundary observable; restrict regression to a single regime; fix the adapter docstring crossing claim | 4a merged | new `_regression_variable_*` helpers; regime-aware fit; tests verifying `R ~ r^(1/2)` super-critically with declared tolerance |
| **4c** | simulation regime audit — adaptive burn-in (≥ 10 · τ_relax), adaptive window (≥ 100 · τ_relax), `N_IC ≥ 32`, mandatory stationarity gate that emits `INCONCLUSIVE` on failure | 4b merged | new tests verifying convergence at near-critical points; adapter version bump |
| **4d** | canonical re-derive — run Phase 3 null-screen at `M = 10000` with the redefined observables and the canonical coordinate; surface `result_hash`, `γ̂_obs`, CI per family; build a `ledger_update` proposal block | 4a, 4b, 4c merged | new evidence JSON; ledger PR proposal (separate human-reviewed PR), no direct mutation |

Each PR is reviewable on its own. None mixes substrate-science with
measurement-governance — the latter is sealed by Phase 3 / PR #161.

## 9. Forbidden Conclusions

This protocol must not claim, and any prose, code, or PR text under
this protocol must not assert:

* "γ ≈ 1 validated"
* "substrate validated"
* "old ledger value preserved"
* "Phase 4 fixed the hypothesis"
* "Theil–Sen killed the hypothesis"
* "log-uniform sweep is automatically correct"
* "raw c is automatically wrong"

The first three are CANON_VALIDATED_FROZEN-class violations and are
already rejected by the schema gate. The last four are
methodological overclaims — they assert a verdict the boundary trace
has not earned.

The correct conclusion of Phase 4a is exactly:

> The substrate boundary is not yet admissible enough for a final γ
> claim. The boundary trace is declared. Two of its observables are
> UNDER_DEFINED_TRACE. The coordinate is SUSPECT. Phase 4b/4c/4d
> may, jointly, render it admissible. None of them, individually, is
> sufficient.

## 10. How to update this protocol

Any change to:

* an observable's `boundary_meaning` (`TODO_OR_FOUND` → declared),
* an observable's `expected_null_behavior`,
* a coordinate's `status`,
* an invariant's `enforcement_status`,
* the `forbidden_claims` list,

must:

1. land in the YAML contract first,
2. update this protocol's prose section,
3. pass `tools/audit/horizon_trace_lint.py` fail-closed checks,
4. pass `tests/test_phase_4a_horizon_trace_contract.py`.

A PR that changes `adapter.py` without an accompanying contract
update is — per `invariants.observable_definition.missing_enforcement`
above — explicitly out of contract, and a future CI gate (Phase 4b)
will reject it.

`claim_status: derived`
