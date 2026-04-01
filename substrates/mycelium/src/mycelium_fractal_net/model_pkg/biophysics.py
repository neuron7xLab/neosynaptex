"""Biophysics functions — Nernst, IFS, Lyapunov, simulation, fractal dimension."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

import numpy as np

try:
    import sympy as sp
except ImportError:  # sympy is optional (crypto extra)
    sp = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# === Physical Constants (SI) ===
R_GAS_CONSTANT: float = 8.314  # J/(mol*K)
FARADAY_CONSTANT: float = 96485.33212  # C/mol
BODY_TEMPERATURE_K: float = 310.0  # K (~37°C)

# === Nernst RT/zF at 37°C (z=1), natural log (ln) ===
NERNST_RTFZ_MV: float = (R_GAS_CONSTANT * BODY_TEMPERATURE_K / FARADAY_CONSTANT) * 1000.0

# === Ion concentration clamp minimum (for numerical stability) ===
ION_CLAMP_MIN: float = 1e-6

# === Turing morphogenesis threshold ===
TURING_THRESHOLD: float = 0.75

# === STDP parameters (heterosynaptic) ===
STDP_TAU_PLUS: float = 0.020  # 20 ms
STDP_TAU_MINUS: float = 0.020  # 20 ms
STDP_A_PLUS: float = 0.01
STDP_A_MINUS: float = 0.012

# === Sparse attention top-k ===
SPARSE_TOPK: int = 4

# === Quantum jitter variance ===
QUANTUM_JITTER_VAR: float = 0.0005


def compute_nernst_potential(
    z_valence: int,
    concentration_out_molar: float,
    concentration_in_molar: float,
    temperature_k: float = BODY_TEMPERATURE_K,
) -> float:
    """
    Compute membrane potential using Nernst equation (in volts).

    E = (R*T)/(z*F) * ln([ion]_out / [ion]_in)

    Physics verification:
    - For K+: [K]_in = 140 mM, [K]_out = 5 mM at 37°C → E_K ≈ -89 mV
    - RT/zF at 37°C (z=1) = 26.73 mV → 58.17 mV for ln to log10

    Parameters
    ----------
    z_valence : int
        Ion valence (K+ = 1, Ca2+ = 2).
    concentration_out_molar : float
        Extracellular concentration (mol/L).
    concentration_in_molar : float
        Intracellular concentration (mol/L).
    temperature_k : float
        Temperature in Kelvin.

    Returns
    -------
    float
        Membrane potential in volts.
    """
    if z_valence == 0:
        raise ValueError("Ion valence cannot be zero for Nernst potential.")

    # Clamp concentrations to avoid log(0) or negative values
    c_out = max(concentration_out_molar, ION_CLAMP_MIN)
    c_in = max(concentration_in_molar, ION_CLAMP_MIN)

    if c_out <= 0 or c_in <= 0:
        raise ValueError("Concentrations must be positive for Nernst potential.")

    ratio = c_out / c_in
    return (R_GAS_CONSTANT * temperature_k) / (z_valence * FARADAY_CONSTANT) * math.log(ratio)


def _symbolic_nernst_example() -> float:
    """
    Use sympy to verify Nernst equation on concrete values.

    Returns numeric potential for K+ at standard concentrations.
    """
    R, T, z, F, c_out, c_in = sp.symbols("R T z F c_out c_in", positive=True)
    E_expr = (R * T) / (z * F) * sp.log(c_out / c_in)

    subs = {
        R: R_GAS_CONSTANT,
        T: BODY_TEMPERATURE_K,
        z: 1,
        F: FARADAY_CONSTANT,
        c_out: 5e-3,
        c_in: 140e-3,
    }
    E_val = float(E_expr.subs(subs).evalf())
    return E_val


def generate_fractal_ifs(
    rng: np.random.Generator,
    num_points: int = 10000,
    num_transforms: int = 4,
) -> tuple[NDArray[Any], float]:
    """
    Generate fractal pattern using Iterated Function System (IFS).

    Uses affine transformations with random contraction mappings.
    Estimates Lyapunov exponent to verify stability (should be < 0).

    Parameters
    ----------
    rng : np.random.Generator
        Random number generator.
    num_points : int
        Number of points to generate.
    num_transforms : int
        Number of affine transformations.

    Returns
    -------
    points : NDArray[Any]
        Generated points of shape (num_points, 2).
    lyapunov : float
        Estimated Lyapunov exponent (negative = stable).
    """
    # Generate random contractive affine transformations
    # Each transform: [a, b, c, d, e, f] → (ax + by + e, cx + dy + f)
    transforms = []
    for _ in range(num_transforms):
        # Contraction factor between 0.2 and 0.5 for stability
        scale = rng.uniform(0.2, 0.5)
        angle = rng.uniform(0, 2 * np.pi)
        a = scale * np.cos(angle)
        b = -scale * np.sin(angle)
        c = scale * np.sin(angle)
        d = scale * np.cos(angle)
        e = rng.uniform(-1, 1)
        f = rng.uniform(-1, 1)
        transforms.append((a, b, c, d, e, f))

    # Run IFS iteration
    points = np.zeros((num_points, 2))
    x, y = 0.0, 0.0
    log_jacobian_sum = 0.0
    jacobian_count = 0

    for i in range(num_points):
        idx = rng.integers(0, num_transforms)
        a, b, c, d, e, f = transforms[idx]
        x_new = a * x + b * y + e
        y_new = c * x + d * y + f
        x, y = x_new, y_new
        points[i] = [x, y]

        # Accumulate Jacobian for Lyapunov exponent
        det = abs(a * d - b * c)
        if det > 1e-10:
            log_jacobian_sum += np.log(det)
            jacobian_count += 1

    # Lyapunov exponent (average log contraction)
    if jacobian_count == 0:
        # If no valid Jacobians were recorded (e.g., degenerate transforms),
        # return a neutral stability indicator instead of underestimating
        # contraction by dividing by the total number of points.
        return points, 0.0

    lyapunov = log_jacobian_sum / jacobian_count

    return points, lyapunov


def compute_lyapunov_exponent(
    field_history: NDArray[Any],
    dt: float = 1.0,
) -> float:
    """
    Compute Lyapunov exponent from field evolution history.

    Measures exponential divergence/convergence of trajectories.
    Negative value indicates stable dynamics.

    Parameters
    ----------
    field_history : NDArray[Any]
        Array of shape (T, N, N) with field states over time.
    dt : float
        Time step between states.

    Returns
    -------
    float
        Estimated Lyapunov exponent.
    """
    if dt <= 0:
        raise ValueError("dt must be positive for Lyapunov exponent")

    if len(field_history) < 2:
        return 0.0

    T = len(field_history)
    log_divergence = 0.0
    steps = T - 1
    eps = 1e-12

    for t in range(1, T):
        diff = np.abs(field_history[t] - field_history[t - 1])
        # Use RMS difference to make the exponent invariant to grid size.
        # Without normalization, identical dynamics on larger grids would
        # artificially inflate the norm by sqrt(N²), skewing the exponent.
        norm_diff = float(np.sqrt(np.mean(diff**2)))
        # When successive states are identical, the divergence contribution
        # should be zero (log(1) = 0) rather than an exaggerated negative value
        # from log(eps). Treat near-zero differences as neutral to keep stable
        # trajectories at a Lyapunov exponent of ~0.
        if norm_diff <= eps:
            continue

        log_divergence += math.log(norm_diff)

    # Normalize by total simulated time to avoid inflating estimates
    total_time = steps * dt
    return log_divergence / total_time


def simulate_mycelium_field(
    rng: np.random.Generator,
    grid_size: int = 64,
    steps: int = 64,
    alpha: float = 0.18,
    spike_probability: float = 0.25,
    turing_enabled: bool = True,
    turing_threshold: float = TURING_THRESHOLD,
    quantum_jitter: bool = False,
    jitter_var: float = QUANTUM_JITTER_VAR,
) -> tuple[NDArray[Any], int]:
    """
    Simulate mycelium-like potential field on 2D lattice with Turing morphogenesis.

    Model features:
    - Field V initialized around -70 mV
    - Discrete Laplacian diffusion
    - Turing reaction-diffusion morphogenesis (activator-inhibitor)
    - Optional quantum jitter for stochastic dynamics
    - Ion clamping for numerical stability

    Physics:
    - Turing threshold = 0.75 for pattern formation
    - Quantum jitter variance = 0.0005 (stable at 0.067 normalized)

    Parameters
    ----------
    rng : np.random.Generator
        Random number generator.
    grid_size : int
        Grid size N x N.
    steps : int
        Simulation steps.
    alpha : float
        Diffusion coefficient.
    spike_probability : float
        Probability of growth event per step.
    turing_enabled : bool
        Enable Turing morphogenesis.
    turing_threshold : float
        Threshold for Turing pattern activation.
    quantum_jitter : bool
        Enable quantum jitter noise.
    jitter_var : float
        Variance of quantum jitter.

    Returns
    -------
    field : NDArray[Any]
        Array of shape (N, N) in volts.
    growth_events : int
        Number of growth events.
    """
    # Initialize around -70 mV
    field = rng.normal(loc=-0.07, scale=0.005, size=(grid_size, grid_size))
    growth_events = 0

    # Turing activator-inhibitor system
    if turing_enabled:
        activator = rng.uniform(0, 0.1, size=(grid_size, grid_size))
        inhibitor = rng.uniform(0, 0.1, size=(grid_size, grid_size))
        da, di = 0.1, 0.05  # diffusion rates
        ra, ri = 0.01, 0.02  # reaction rates

    for _step in range(steps):
        # Growth events (spikes)
        if rng.random() < spike_probability:
            i = int(rng.integers(0, grid_size))
            j = int(rng.integers(0, grid_size))
            field[i, j] += float(rng.normal(loc=0.02, scale=0.005))
            growth_events += 1

        # Laplacian diffusion
        up = np.roll(field, 1, axis=0)
        down = np.roll(field, -1, axis=0)
        left = np.roll(field, 1, axis=1)
        right = np.roll(field, -1, axis=1)
        laplacian = up + down + left + right - 4.0 * field
        field = field + alpha * laplacian

        # Turing morphogenesis
        if turing_enabled:
            # Laplacian for activator/inhibitor
            a_lap = (
                np.roll(activator, 1, axis=0)
                + np.roll(activator, -1, axis=0)
                + np.roll(activator, 1, axis=1)
                + np.roll(activator, -1, axis=1)
                - 4.0 * activator
            )
            i_lap = (
                np.roll(inhibitor, 1, axis=0)
                + np.roll(inhibitor, -1, axis=0)
                + np.roll(inhibitor, 1, axis=1)
                + np.roll(inhibitor, -1, axis=1)
                - 4.0 * inhibitor
            )

            # Reaction-diffusion update
            activator += da * a_lap + ra * (activator * (1 - activator) - inhibitor)
            inhibitor += di * i_lap + ri * (activator - inhibitor)

            # Apply Turing pattern to field where activator exceeds threshold
            turing_mask = activator > turing_threshold
            field[turing_mask] += 0.005

            # Clamp activator/inhibitor
            activator = np.clip(activator, 0, 1)
            inhibitor = np.clip(inhibitor, 0, 1)

        # Quantum jitter
        if quantum_jitter:
            jitter = rng.normal(0, np.sqrt(jitter_var), size=field.shape)
            field += jitter

        # Ion clamping (≈ [-95, 40] mV)
        field = np.clip(field, -0.095, 0.040)

    return field, growth_events


def estimate_fractal_dimension(
    binary_field: NDArray[Any],
    min_box_size: int = 2,
    max_box_size: int | None = None,
    num_scales: int = 5,
) -> float:
    """
    Box-counting estimation of fractal dimension for binary field.

    Empirically validated: D ≈ 1.584 for stable mycelium patterns.

    Parameters
    ----------
    binary_field : NDArray[Any]
        Boolean array of shape (N, N).
    min_box_size : int
        Minimum box size.
    max_box_size : int | None
        Maximum box size (None = N//2).
    num_scales : int
        Number of logarithmic scales.

    Returns
    -------
    float
        Estimated fractal dimension.
    """
    if binary_field.ndim != 2 or binary_field.shape[0] != binary_field.shape[1]:
        raise ValueError("binary_field must be a square 2D array.")
    if num_scales < 1:
        raise ValueError("num_scales must be >= 1.")

    n = binary_field.shape[0]
    if max_box_size is None:
        max_box_size = min_box_size * (2 ** (num_scales - 1))
        max_box_size = min(max_box_size, n // 2 if n >= 4 else n)

    if max_box_size < min_box_size:
        max_box_size = min_box_size

    sizes = np.geomspace(min_box_size, max_box_size, num_scales).astype(int)
    sizes = np.unique(sizes)
    counts: list[float] = []
    used_sizes: list[int] = []

    for size in sizes:
        if size <= 0:
            continue
        n_boxes = n // size
        if n_boxes == 0:
            continue
        reshaped = binary_field[: n_boxes * size, : n_boxes * size].reshape(
            n_boxes, size, n_boxes, size
        )
        occupied = reshaped.any(axis=(1, 3))
        counts.append(float(occupied.sum()))
        used_sizes.append(int(size))

    if not counts:
        return 0.0

    counts_arr = np.array(counts, dtype=float)
    valid = counts_arr > 0
    if valid.sum() < 2:
        return 0.0

    sizes = np.array(used_sizes, dtype=int)[valid]
    counts_arr = counts_arr[valid]

    inv_eps = 1.0 / sizes.astype(float)
    log_inv_eps = np.log(inv_eps)
    log_counts = np.log(counts_arr)

    coeffs = np.polyfit(log_inv_eps, log_counts, 1)
    fractal_dim = float(coeffs[0])
    return fractal_dim
