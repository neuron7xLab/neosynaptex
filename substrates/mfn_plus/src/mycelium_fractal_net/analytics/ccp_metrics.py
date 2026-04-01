"""
Cognitive Criticality Principle (CCP) Metrics.

Measures the CCP triple K = <D_f, Phi, R> for FieldSequence:
- D_f: Box-counting fractal dimension (cognitive window [1.5, 2.0])
- Phi: Integrated information proxy via causal emergence
- R: Kuramoto phase coherence order parameter

Theorem 1 (CCP): A system is cognitive iff D_f in [1.5, 2.0] AND Phi > Phi_c AND R > R_c.

Refs:
    Vasylenko CCP (2026)
    Beggs & Plenz (2003) — neuronal avalanches, doi:10.1523/JNEUROSCI.23-35-11167.2003
    Tononi (2004) — integrated information, doi:10.1186/1471-2202-5-42
    Hoel et al. (2013) — causal emergence, doi:10.1073/pnas.1314922110
    Kuramoto (1984) — Chemical Oscillations, Waves and Turbulence
    Cabral et al. (2014) — phase coherence, doi:10.1016/j.neuroimage.2013.09.062
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.analytics.legacy_features import (
    FeatureConfig,
)
from mycelium_fractal_net.analytics.legacy_features import (
    compute_fractal_features as _compute_fractal_dim_r2,
)
from mycelium_fractal_net.types.field import FieldSequence

if TYPE_CHECKING:
    from numpy.typing import NDArray

# CCP thresholds
D_F_MIN = 1.5
D_F_MAX = 2.0
R_C = 0.4      # Kuramoto critical threshold
PHI_C = 0.0    # Causal emergence threshold (CE > 0)


def compute_fractal_dimension(seq: FieldSequence) -> dict:
    """
    Compute D_f (box-counting fractal dimension) of the field.

    CCP prediction: D_f in [1.5, 2.0] for cognitive systems.

    Uses adaptive threshold (mean + 0.25*std) for binarization,
    which isolates the structured active region rather than
    treating the entire field as active.

    Ref: Beggs & Plenz (2003), Vasylenko CCP (2026)
    """
    field = seq.field.astype(np.float64)

    # Adaptive threshold: mean + 0.25*std (in mV for FeatureConfig)
    # This discriminates structured activity from background
    mean_mv = float(np.mean(field)) * 1000.0
    std_mv = float(np.std(field)) * 1000.0
    threshold_mv = mean_mv + 0.25 * std_mv

    config = FeatureConfig(num_scales=8, threshold_low_mv=threshold_mv)
    D_box, D_r2 = _compute_fractal_dim_r2(field, config)

    return {
        "D_f": float(D_box),
        "D_r2": float(D_r2),
        "in_cognitive_window": D_F_MIN <= D_box <= D_F_MAX,
        "D_min": D_F_MIN,
        "D_max": D_F_MAX,
        "ref": "Vasylenko CCP (2026), Beggs & Plenz (2003)",
    }


def compute_integrated_information_proxy(seq: FieldSequence) -> dict:
    """
    Compute Phi proxy through causal emergence (Hoel et al. 2013).

    Uses effective information (EI) at micro vs macro level.
    CE = EI_macro - EI_micro. CE > 0 => Phi > Phi_c.

    For a 2D field: macro = coarse-grained (2x2 blocks),
    micro = pixel-level transition statistics.

    Ref: Hoel et al. (2013) PNAS, Tononi (2004)
    """
    field = seq.field.astype(np.float64)

    # EI_micro: entropy of pixel-level transition matrix
    # Use spatial gradients as proxy for transition dynamics
    dx = np.diff(field, axis=1)
    dy = np.diff(field, axis=0)
    micro_var = float(np.var(dx) + np.var(dy))
    # EI = log(det) proxy: higher variance = higher entropy
    EI_micro = float(np.log1p(micro_var * 1000.0))

    # EI_macro: coarse-grain to 2x2 blocks
    N = field.shape[0]
    n2 = N // 2
    if n2 >= 2:
        coarse = field[:n2*2, :n2*2].reshape(n2, 2, n2, 2).mean(axis=(1, 3))
        dx_c = np.diff(coarse, axis=1)
        dy_c = np.diff(coarse, axis=0)
        macro_var = float(np.var(dx_c) + np.var(dy_c))
        EI_macro = float(np.log1p(macro_var * 1000.0))
    else:
        EI_macro = EI_micro

    phi_proxy = EI_macro - EI_micro

    return {
        "phi_proxy": float(phi_proxy),
        "above_threshold": phi_proxy > PHI_C,
        "EI_micro": float(EI_micro),
        "EI_macro": float(EI_macro),
        "ref": "Hoel et al. (2013) PNAS, Tononi (2004)",
    }


def compute_phase_coherence(seq: FieldSequence) -> dict:
    """
    Compute Kuramoto order parameter R for the field.

    R = |1/N * sum(exp(i*theta_j))| where theta_j = phase of each node.

    For 2D field without temporal data: use spatial Hilbert-like phase
    from the field values via arctan2 of spatial gradients.

    With temporal history: use temporal phase via Hilbert transform.

    CCP threshold: R > R_c ~ 0.4

    Ref: Kuramoto (1984), Cabral et al. (2014)
    """
    if seq.history is not None and seq.history.shape[0] >= 4:
        # Temporal phase coherence via analytic signal
        history = seq.history.astype(np.float64)
        T, _N, _M = history.shape
        # Compute phase per node across time using discrete derivative
        # Phase approx: arctan2(dx/dt derivative, x - mean)
        flat = history.reshape(T, -1)  # (T, N*M)
        mean_signal = flat.mean(axis=0, keepdims=True)
        centered = flat - mean_signal

        # Simple phase via Hilbert-like: phase = arctan2(derivative, signal)
        deriv = np.diff(centered, axis=0)  # (T-1, N*M)
        sig = centered[:-1, :]  # align
        phases = np.arctan2(deriv, sig + 1e-12)  # (T-1, N*M)

        # Average Kuramoto R over time
        R_per_t = np.abs(np.mean(np.exp(1j * phases), axis=1))  # (T-1,)
        R = float(np.mean(R_per_t))
    else:
        # Spatial phase coherence for single frame
        field = seq.field.astype(np.float64)
        # Spatial gradients as phase proxy
        dx = np.gradient(field, axis=1)
        dy = np.gradient(field, axis=0)
        phases = np.arctan2(dy, dx + 1e-12)
        R = float(np.abs(np.mean(np.exp(1j * phases))))

    return {
        "R": float(np.clip(R, 0.0, 1.0)),
        "R_c": R_C,
        "above_threshold": R > R_C,
        "ref": "Kuramoto (1984), Cabral et al. (2014)",
    }


def compute_ccp_state(seq: FieldSequence) -> dict:
    """
    Compute full CCP state: K = <D_f, Phi, R>.

    Theorem 1 (CCP): cognitive iff D_f in [1.5, 2.0] AND Phi > Phi_c AND R > R_c.

    Ref: Vasylenko CCP (2026)
    """
    df = compute_fractal_dimension(seq)
    phi = compute_integrated_information_proxy(seq)
    r = compute_phase_coherence(seq)

    conditions = [
        df["in_cognitive_window"],
        phi["above_threshold"],
        r["above_threshold"],
    ]
    conditions_met = sum(conditions)
    cognitive = all(conditions)

    ccp_summary = (
        f"D_f={df['D_f']:.3f} ({'in' if df['in_cognitive_window'] else 'out'} window) | "
        f"Phi={phi['phi_proxy']:.3f} ({'>' if phi['above_threshold'] else '<='} 0) | "
        f"R={r['R']:.3f} ({'>' if r['above_threshold'] else '<='} {R_C}) | "
        f"cognitive={cognitive}"
    )

    return {
        "D_f": df["D_f"],
        "D_r2": df["D_r2"],
        "phi_proxy": phi["phi_proxy"],
        "R": r["R"],
        "cognitive": cognitive,
        "conditions_met": conditions_met,
        "ccp_summary": ccp_summary,
        "details": {"fractal": df, "phi": phi, "coherence": r},
        "ref": "Vasylenko CCP (2026)",
    }


def ccp_trajectory(history: NDArray[np.float64]) -> dict:
    """
    Track CCP state through time.

    For each step in history, compute D_f, Phi proxy, R.
    Determine when the system enters/exits the cognitive window.

    Args:
        history: 3D array (T, N, N) — temporal field evolution.

    Returns:
        D_f, R, phi trajectories, cognitive_steps, cognitive_fraction, transitions.
    """
    if history.ndim != 3:
        raise ValueError(f"history must be 3D (T, N, N), got {history.ndim}D")

    T, N, _M = history.shape
    D_f_traj = []
    R_traj = []
    phi_traj = []
    cognitive_mask = []

    for t in range(T):
        frame = history[t]

        # D_f with adaptive threshold
        mean_mv = float(np.mean(frame)) * 1000.0
        std_mv = float(np.std(frame)) * 1000.0
        thr_mv = mean_mv + 0.25 * std_mv
        config = FeatureConfig(num_scales=min(8, max(2, N // 4)), threshold_low_mv=thr_mv)
        D_box, _ = _compute_fractal_dim_r2(frame, config)
        D_f_traj.append(float(D_box))

        # Phi proxy (simplified for speed)
        dx = np.diff(frame, axis=1)
        dy = np.diff(frame, axis=0)
        micro_var = float(np.var(dx) + np.var(dy))
        EI_micro = float(np.log1p(micro_var * 1000.0))
        n2 = N // 2
        if n2 >= 2:
            coarse = frame[:n2*2, :n2*2].reshape(n2, 2, n2, 2).mean(axis=(1, 3))
            dx_c = np.diff(coarse, axis=1)
            dy_c = np.diff(coarse, axis=0)
            macro_var = float(np.var(dx_c) + np.var(dy_c))
            EI_macro = float(np.log1p(macro_var * 1000.0))
        else:
            EI_macro = EI_micro
        phi_traj.append(float(EI_macro - EI_micro))

        # R (spatial for single frame)
        gx = np.gradient(frame, axis=1)
        gy = np.gradient(frame, axis=0)
        phases = np.arctan2(gy, gx + 1e-12)
        R_val = float(np.abs(np.mean(np.exp(1j * phases))))
        R_traj.append(float(np.clip(R_val, 0.0, 1.0)))

        # Cognitive check
        cog = (D_F_MIN <= D_f_traj[-1] <= D_F_MAX) and (phi_traj[-1] > PHI_C) and (R_traj[-1] > R_C)
        cognitive_mask.append(cog)

    cognitive_steps = sum(cognitive_mask)
    cognitive_fraction = cognitive_steps / max(1, T)

    # Transitions: indices where cognitive state changes
    transitions = []
    for i in range(1, len(cognitive_mask)):
        if cognitive_mask[i] != cognitive_mask[i-1]:
            transitions.append(i)

    return {
        "D_f_trajectory": D_f_traj,
        "R_trajectory": R_traj,
        "phi_trajectory": phi_traj,
        "cognitive_steps": cognitive_steps,
        "cognitive_fraction": float(cognitive_fraction),
        "transitions": transitions,
    }


# ===================================================================
# TESTS
# ===================================================================


def _make_spots_field(N=32, seed=42):
    """Structured spots pattern — should have D_f in cognitive window."""
    rng = np.random.RandomState(seed)
    field = np.full((N, N), -0.080, dtype=np.float64)
    for _ in range(N * N // 8):
        cx, cy = rng.randint(0, N, 2)
        r = rng.randint(1, max(2, N // 8))
        y, x = np.ogrid[-cx:N-cx, -cy:N-cy]
        mask = x*x + y*y <= r*r
        field[mask] = rng.uniform(-0.040, 0.010)
    return FieldSequence(field=field)


def _make_noise_field(N=32, seed=99):
    """Pure random noise — D_f should be near 2.0 or outside cognitive window."""
    rng = np.random.RandomState(seed)
    field = rng.uniform(-0.095, 0.040, (N, N))
    return FieldSequence(field=field)


def _make_structured_field(N=32, seed=42):
    """Structured field with clear spatial organization."""
    rng = np.random.RandomState(seed)
    x = np.linspace(0, 4*np.pi, N)
    y = np.linspace(0, 4*np.pi, N)
    X, Y = np.meshgrid(x, y)
    field = (np.sin(X) * np.cos(Y) * 0.03 - 0.060).astype(np.float64)
    field += rng.normal(0, 0.002, (N, N))
    return FieldSequence(field=field)


def _make_field_with_history(N=16, T=20, seed=42):
    """Field with temporal history for phase coherence."""
    rng = np.random.RandomState(seed)
    history = np.zeros((T, N, N), dtype=np.float64)
    for t in range(T):
        x = np.linspace(0, 2*np.pi, N)
        y = np.linspace(0, 2*np.pi, N)
        X, Y = np.meshgrid(x, y)
        history[t] = np.sin(X + t * 0.3) * np.cos(Y) * 0.03 - 0.060
        history[t] += rng.normal(0, 0.001, (N, N))
    field = history[-1]
    return FieldSequence(field=field, history=history)


def _tests_fractal_dimension(test_fn) -> None:
    print("\n--- Fractal dimension ---")

    def _test_D_f_spots():
        seq = _make_spots_field()
        result = compute_fractal_dimension(seq)
        assert "D_f" in result
        assert "D_r2" in result
        assert 0.0 <= result["D_f"] <= 2.5, f"D_f={result['D_f']} out of range"
    test_fn("D_f for spots pattern has valid range", _test_D_f_spots)

    def _test_D_f_noise():
        seq = _make_noise_field()
        result = compute_fractal_dimension(seq)
        assert result["D_f"] >= 1.0, f"noise D_f={result['D_f']} unexpectedly low"
    test_fn("D_f for noise >= 1.0", _test_D_f_noise)

    def _test_D_f_returns_all_keys():
        seq = _make_spots_field()
        result = compute_fractal_dimension(seq)
        for key in ["D_f", "D_r2", "in_cognitive_window", "D_min", "D_max", "ref"]:
            assert key in result, f"missing key: {key}"
    test_fn("compute_fractal_dimension returns all keys", _test_D_f_returns_all_keys)


def _tests_phi_proxy(test_fn) -> None:
    print("\n--- Integrated information proxy ---")

    def _test_phi_structured():
        seq = _make_structured_field()
        result = compute_integrated_information_proxy(seq)
        assert "phi_proxy" in result
        assert "EI_micro" in result
        assert "EI_macro" in result
    test_fn("Phi proxy returns all keys for structured field", _test_phi_structured)

    def _test_phi_has_value():
        seq = _make_spots_field()
        result = compute_integrated_information_proxy(seq)
        assert isinstance(result["phi_proxy"], float)
    test_fn("Phi proxy is float", _test_phi_has_value)


def _tests_phase_coherence(test_fn) -> None:
    print("\n--- Phase coherence ---")

    def _test_R_structured():
        seq = _make_structured_field()
        result = compute_phase_coherence(seq)
        assert 0.0 <= result["R"] <= 1.0, f"R={result['R']} out of [0,1]"
    test_fn("R in [0,1] for structured field", _test_R_structured)

    def _test_R_with_history():
        seq = _make_field_with_history()
        result = compute_phase_coherence(seq)
        assert 0.0 <= result["R"] <= 1.0
        assert "R_c" in result
    test_fn("R with temporal history", _test_R_with_history)


def _tests_ccp_state(test_fn) -> None:
    print("\n--- CCP state ---")

    def _test_ccp_state_structured():
        seq = _make_structured_field()
        result = compute_ccp_state(seq)
        assert "D_f" in result
        assert "phi_proxy" in result
        assert "R" in result
        assert "cognitive" in result
        assert "conditions_met" in result
        assert 0 <= result["conditions_met"] <= 3
    test_fn("CCP state for structured field", _test_ccp_state_structured)

    def _test_ccp_cognitive_is_bool():
        seq = _make_spots_field()
        result = compute_ccp_state(seq)
        assert isinstance(result["cognitive"], bool)
    test_fn("CCP cognitive is bool", _test_ccp_cognitive_is_bool)

    def _test_conditions_met_range():
        for fn in [_make_spots_field, _make_noise_field, _make_structured_field]:
            seq = fn()
            result = compute_ccp_state(seq)
            assert 0 <= result["conditions_met"] <= 3
    test_fn("conditions_met in [0, 3] for various fields", _test_conditions_met_range)

    def _test_ccp_summary_not_empty():
        seq = _make_spots_field()
        result = compute_ccp_state(seq)
        assert len(result["ccp_summary"]) > 0
    test_fn("CCP summary not empty", _test_ccp_summary_not_empty)


def _tests_ccp_trajectory(test_fn) -> None:
    print("\n--- CCP trajectory ---")

    def _test_trajectory_returns_all_fields():
        history = _make_field_with_history(N=16, T=10).history
        result = ccp_trajectory(history)
        for key in ["D_f_trajectory", "R_trajectory", "phi_trajectory",
                     "cognitive_steps", "cognitive_fraction", "transitions"]:
            assert key in result, f"missing key: {key}"
    test_fn("ccp_trajectory returns all fields", _test_trajectory_returns_all_fields)

    def _test_trajectory_lengths():
        T, N = 10, 16
        history = _make_field_with_history(N=N, T=T).history
        result = ccp_trajectory(history)
        assert len(result["D_f_trajectory"]) == T
        assert len(result["R_trajectory"]) == T
        assert len(result["phi_trajectory"]) == T
    test_fn("trajectory lengths match T", _test_trajectory_lengths)

    def _test_cognitive_fraction_range():
        history = _make_field_with_history(N=16, T=10).history
        result = ccp_trajectory(history)
        assert 0.0 <= result["cognitive_fraction"] <= 1.0
    test_fn("cognitive_fraction in [0, 1]", _test_cognitive_fraction_range)

    def _test_trajectory_invalid_input():
        try:
            ccp_trajectory(np.zeros((10, 10)))  # 2D instead of 3D
            raise AssertionError("should raise ValueError")
        except ValueError:
            pass
    test_fn("ccp_trajectory rejects 2D input", _test_trajectory_invalid_input)


def _run_tests() -> None:
    passed = 0
    failed = 0
    errors: list[str] = []

    def _test(name, fn):
        nonlocal passed, failed
        try:
            fn()
            passed += 1
            print(f"  \u2713 {name}")
        except Exception as e:
            failed += 1
            errors.append(f"  \u2717 {name}: {e}")
            print(f"  \u2717 {name}: {e}")

    print("=" * 60)
    print("CCP Metrics Test Suite")
    print("=" * 60)

    _tests_fractal_dimension(_test)
    _tests_phi_proxy(_test)
    _tests_phase_coherence(_test)
    _tests_ccp_state(_test)
    _tests_ccp_trajectory(_test)

    # --- Summary ---
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if errors:
        print("\nFailed tests:")
        for e in errors:
            print(e)
    print("=" * 60)
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    _run_tests()
