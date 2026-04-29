# Phase 4b: Canonical Kuramoto Boundary Observables

**Status:** frozen prose. Content changes require a protocol-version
bump. Phase 4b is a substrate-science PR; it is independent of the
measurement-governance Phase 3.

**Authoritative modules:**
* `core/exponent_measurement.py` — coordinate contract.
* `substrates/serotonergic_kuramoto/observables.py` — boundary
  observable contract.

**Authoritative test:** `tests/test_kuramoto_canonical.py`.

**Verdict ceiling for this PR:** code runs, schema is valid,
observables are deterministic, no forbidden claim appears, legacy
γ-claim path is documented as deprecated. **This PR does not measure
γ̂. It does not require β = 0.5 to pass CI.** The β fit on real
substrate data is Phase 4d.

## 1. Why `topo` and `thermo_cost` are deprecated for γ-claims

The legacy NFI projection

    γ̂ ← −slope of   log(thermo_cost) vs log(topo)   over the c-axis

was the path that produced `γ̂ ≈ 1.0677` (linear C, N=20, sorted-OLS;
v1 ledger), `γ̂ ≈ 0.7403` (log-uniform C, N=128, sorted-OLS; v2
patch), and `γ̂ ≈ 0.0661` (log-uniform C, N=128, canonical Theil–Sen;
v2 patch). A factor-of-16 spread of "the same number" across
estimator and sweep choices is the structural diagnostic that the
projection is **not** a measurement of substrate physics — it is a
function of interface choice.

The Phase 4a horizon-trace audit (`horizon_trace_contract.yaml`)
flagged both observables as `UNDER_DEFINED_TRACE`:

* `topo` is a single-time pair count over `(i < j)` pairs with
  `|sin(θ_i − θ_j)| > 0.3`. The threshold 0.3 has no theoretical
  justification in code or docs. The metric is not a topological
  invariant; it has no Kuramoto-theory scaling expectation. It is a
  project-specific interface construct.
* `thermo_cost` is a time-averaged L1 norm of the mean-field coupling
  drive. The L1 choice is unjustified (mean-field "work" is canonically
  L2 / energy-like). It scales linearly with `K_eff` by construction,
  so any apparent K-dependence is entangled with the modulation knob.
  No `kT`, no entropy, no fluctuation-dissipation linkage — the name
  "thermo" is a misnomer.

Phase 4b therefore deprecates both for **canonical Kuramoto γ-claims**.
They remain callable as `adapter.topo()` and `adapter.thermo_cost()`
because legacy readers depend on them; the deprecation is a
constraint on what kind of claim they may ground, not a code removal.

## 2. Canonical observables

The canonical Kuramoto boundary observables are exposed in
`substrates/serotonergic_kuramoto/observables.py`:

| function | symbol | shape in / out | meaning |
|---|---|---|---|
| `instantaneous_R(theta_snapshot)` | `R(t)` | `(N,)` → `float` in `[0, 1]` | mean-field order parameter at one time step |
| `order_parameter_R_timeseries(theta_history)` | `R(t)` series | `(T, N)` → `(T,)` | per-time-step order parameter on a phase history |
| `order_parameter_R(theta_history)` | `R̄` | `(T, N)` → `float` | time-averaged R (the canonical "R_∞" for stationary windows) |
| `susceptibility_chi(R_values, N)` | `χ` | `(T,)`, `int` → `float` | `χ = N · var(R(t))` |

The coordinate contract is in `core/exponent_measurement.py`:

| function | symbol | meaning |
|---|---|---|
| `compute_K_eff(c, K_base, mod_slope)` | `K_eff` | linear pharmacological mapping `K_base · (1 − mod_slope · c)` |
| `compute_K_c_from_frequency_density(omega)` | `K_c` | mean-field `σ_ω · sqrt(8/π)` for a Gaussian frequency draw |
| `compute_reduced_coupling(K_eff, K_c)` | `r` | `(K_eff − K_c) / K_c` — the canonical scaling variable |
| `compute_c_at_critical_crossing(K_base, mod_slope, K_c)` | `c*` | inverse of K_eff: the c-axis value where `K_eff = K_c` |

Both modules export expected exponent constants:
* `EXPECTED_BETA_SUPER_CRITICAL = 0.5` — order-parameter scaling, `R̄ ~ r^(1/2)` for `r > 0`.
* `EXPECTED_GAMMA_SUSCEPTIBILITY = -1.0` — susceptibility scaling, `χ ~ |r|^(-1)` near `r = 0`.

These constants are *theoretical predictions*, not fit results. They
are declared up-front so any future fit can be compared to a number
that exists before the data is taken.

## 3. Primary target — `R̄(r)` for `r > 0`, expected slope `1/2`

The primary canonical γ-claim path on this substrate is

    log R̄  vs  log r       on   r > 0   (super-critical regime).

* Source: Kuramoto 1984 §5; Strogatz 2000 eq. 16; Acebrón et al. RMP
  2005 §III.A.
* Expected slope (mean-field): `β = 0.5`.
* Failure mode: if the measured slope on enough decades of `r` falls
  outside an explicit tolerance, the substrate **falsifies** mean-field
  Kuramoto at this calibration. That is a scientifically valid
  outcome.

The secondary claim path is the susceptibility:

    log χ  vs  log |r|      near `r = 0`.

* Expected slope (mean-field): `γ = -1`.
* This is the "γ" of Kuramoto literature in the strict sense (the
  susceptibility exponent), distinct from the loose "γ" the legacy
  NFI projection produced.

Phase 4b ships only the *building blocks* of these fits. The actual
β-fit and `χ`-fit happen in Phase 4d under the canonical Phase 3
null-screen pipeline.

## 4. Why raw `c` is not the canonical critical coordinate

`c ∈ [0, 1]` is the 5-HT2A pharmacological-modulation knob. It maps
to `K_eff` linearly via `K_base · (1 − mod_slope · c)`. With the
canonical adapter constants (`K_base = 2.0`, `mod_slope = 0.7`,
`σ_op = 0.065 Hz`), the phase transition crosses K_c at:

    K_base · (1 − mod_slope · c*) = K_c
    1 − 0.7 · c* = K_c / K_base = 0.6517 / 2.0 = 0.3258
    c* = (1 − 0.3258) / 0.7 ≈ **0.963**

The adapter docstring (line 43 on main) still claims the crossing
sits at `c ≈ 0.71`. **That value is arithmetically inconsistent with
the adapter's own constants.** Phase 4a horizon-trace audit flagged
this; Phase 4b's `compute_c_at_critical_crossing` and
`tests/test_kuramoto_canonical.py::test_c_crossing_at_canonical_adapter_constants_is_about_0_963`
document the correct value. The adapter source-code docstring fix is
deferred to a follow-up PR (see §6) because changing the adapter file
would invalidate the Phase 2.1 `adapter_code_hash` binding without an
accompanying ledger entry update — a coupled change that belongs in a
PR that explicitly handles the ledger side.

Even if the docstring were correct, raw `c` is still the *wrong*
coordinate for canonical scaling claims, because Kuramoto theory does
not predict scaling against a knob index. It predicts scaling against
the reduced coupling

    r = (K_eff(c) − K_c) / K_c

and only against `r`. A regression on raw `c` mixes two regimes
(super-critical `r > 0` and sub-critical `r < 0`) into one fit,
violates the "single regime per scaling law" rule, and produces a
slope with no theoretical reference.

## 5. Why a negative result is a valid scientific output

The forbidden conclusion of Phase 4 is "the hypothesis is dead." The
allowed one is "the boundary observable and coordinate system are not
yet admissible enough to support a single γ claim." That asymmetry
is structural, not stylistic.

If the canonical fit on `R̄(r)` for `r > 0` returns a slope outside
the expected `0.5 ± tolerance`, that is **also** valid science. It
falsifies mean-field Kuramoto at this calibration — which is itself
a publishable result. A measurement that returns `γ̂ ≈ 0.07` on a
canonical observable, with declared CI and reproducible result_hash,
under a stated null protocol, is a real finding. It says: this
substrate, at this calibration, does not exhibit mean-field
super-critical scaling.

That is what canonical-physics measurement looks like. The boundary
trace is allowed to say "no". Phase 3's ladder includes
`NULL_NOT_REJECTED` and `EVIDENCE_CANDIDATE_NULL_FAILED` precisely so
that the system has structural words for "the hypothesis was
honestly tested and did not hold."

## 6. What remains for Phase 4c, 4d, and the deferred adapter fixes

This PR does not implement:

* **Phase 4c — simulation regime audit:** adaptive burn-in
  (`≥ 10 · τ_relax(K_eff)`), adaptive measurement window
  (`≥ 100 · τ_relax`), `N_IC ≥ 32`, mandatory stationarity gate that
  emits `INCONCLUSIVE` when window-half mean differs by more than the
  declared tolerance.
* **Phase 4d — canonical re-derive:** Phase 3 null-screen on the new
  observables at `M = 10000`, regime-restricted fit (`r > 0` for `β`,
  `|r| < ε` for `χ`), declared expected slope, structural `result_hash`,
  ledger update **proposal-only**.
* **Adapter source-code edits:** the docstring crossing claim
  (`c ≈ 0.71` → `c ≈ 0.963`), public `order_parameter()` /
  `reduced_coupling()` adapter methods, and explicit deprecation
  markers on `topo()`/`thermo_cost()` docstrings. These are deferred
  because changing `substrates/serotonergic_kuramoto/adapter.py`
  invalidates the Phase 2.1 `adapter_code_hash` binding; the binding
  update is structural ledger maintenance and must travel in the
  same PR. That coupled PR (Phase 4b-2) is small but explicit; this
  one keeps strict scope by adding only new files.

This PR also does not promote `topo`/`thermo_cost` to Phase 4d —
they stay deprecated. They do not get rehabilitated. They will not be
the basis of any future Kuramoto exponent claim.

## 7. Forbidden claims (gate-enforced)

The following must not appear as positive assertions in any Phase 4
artefact:

* `γ≈1 validated`
* `substrate validated`
* `Phase 4 fixed the hypothesis`
* `old γ preserved`
* `Theil-Sen killed the hypothesis`

`tests/test_kuramoto_canonical.py::test_no_forbidden_claims_in_phase_4b_protocol_doc`
enforces this on the present file. Global `claim_overclaim_gate`
(Phase 2.1) covers production source files.

## 8. Update procedure

Any change to:

* an exposed observable's signature or semantic,
* an expected-exponent constant,
* the canonical regression target or coordinate,
* the deprecation status of `topo`/`thermo_cost`,

must:

1. land in this protocol first,
2. update the corresponding code module(s),
3. update the test(s) that ratify the new behaviour,
4. pass the global `claim_overclaim_gate`.

A PR that changes `core/exponent_measurement.py` or
`substrates/serotonergic_kuramoto/observables.py` without updating
this protocol is — by the contract this protocol declares — explicitly
out of scope, and a future CI gate (Phase 4c) will reject it.

`claim_status: derived`
