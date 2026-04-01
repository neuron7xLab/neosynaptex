# Mathematical Contracts — BN-Syn

## 1. ODE Integration
- **CFL-like stability**: `dt * |λ_max| < 1.0` for Euler and `< 2.785` for RK4 via `assert_dt_stability`.
- **State boundedness**: post-step state vectors must remain finite via `assert_state_finite_after_step`.
- **Energy dissipation/boundedness**: energy time-series must not diverge and cannot increase above tolerance (`1e-4`) via `assert_energy_bounded`.
- **Tolerance consistency**: `atol < dt` and `rtol > eps(float64)` via `assert_integration_tolerance_consistency`.

## 2. Phase Dynamics
- **Phase range**: `θ ∈ [0, 2π)` or `θ ∈ [-π, π)` via `assert_phase_range`.
- **Order parameter bounds**: `r ∈ [0, 1]` (±1e-10) via `assert_order_parameter_range`.
- **Order parameter recomputation**: `r = |(1/N) Σ exp(iθ_j)|` must match reported value via `assert_order_parameter_computation`.
- **Phase velocity finite**: `dθ/dt` cannot contain NaN/Inf via `assert_phase_velocity_finite`.

## 3. Network Topology
- **Coupling matrix**: finite NxN matrix, optional symmetry (`K=Kᵀ`) via `assert_coupling_matrix_properties`.
- **Adjacency matrix**: binary entries `{0,1}` and no self-loops via `assert_adjacency_binary`.
- **Weight matrix physicality**: nonnegative weights via `assert_weight_matrix_nonnegative`.

## 4. Numerical Guards
- **Cancellation detector**: flags >3-digit precision loss contexts via `assert_no_catastrophic_cancellation`.
- **Log domain guard**: requires `x > 0` via `assert_no_log_domain_violation`.
- **Exp overflow guard**: flags `|x| > 500` via `assert_no_exp_overflow_risk`.
- **Division near-zero guard**: flags `|denominator| < 1e-300` via `assert_no_division_by_zero_risk`.
- **Dtype consistency**: prevents silent float32/float64 mixing via `assert_dtype_consistency`.

## 5. Data Integrity
- **No NaN dataset entries** via `assert_no_nan_in_dataset`.
- **No duplicate rows** via `assert_no_duplicate_rows`.
- **Column range constraints** for structured arrays via `assert_column_ranges`.
- **Probability normalization**: `sum(p)=1±1e-8` via `assert_probability_normalization`.
- **Time monotonicity**: strictly increasing time grids via `assert_timeseries_monotonic_time`.

## 6. Validator Categories
- `physics_invariant`
- `numeric_hazard`
- `data_integrity`
- `schema`

## 7. Tolerances
| Check | Absolute | Relative | Rationale |
|---|---:|---:|---|
| Order parameter recomputation | `1e-6` | — | complex summation roundoff |
| Coupling symmetry | `1e-12` | — | matrix construction determinism |
| Probability normalization | `1e-8` | — | floating-point summation |
| Energy monotonic drift | `1e-4` | — | integrator truncation tolerance |
| Order parameter range slack | `1e-10` | — | finite-precision bounds |
