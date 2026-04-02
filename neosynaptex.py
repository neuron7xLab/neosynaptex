"""neosynaptex -- NFI integrating mirror layer.

Single-file convergence module that observes four NFI subsystems
(BN-Syn, MFN+, PsycheCore, mvstack/GeoSync) and computes cross-domain
coherence diagnostics with scientific rigor: bootstrap CI, permutation
tests, Granger causality, phase portraits, anomaly isolation,
resilience proof, and reflexive modulation signals.

Author: Yaroslav Vasylenko (neuron7xLab)
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from scipy.linalg import lstsq as scipy_lstsq
from scipy.spatial import ConvexHull
from scipy.stats import theilslopes

from core.value_function import ValueEstimate, estimate_value

__all__ = [
    "DomainAdapter",
    "NeosynaptexState",
    "Neosynaptex",
    "MockBnSynAdapter",
    "MockMfnAdapter",
    "MockPsycheCoreAdapter",
    "MockMarketAdapter",
    "INITIALIZING",
    "METASTABLE",
    "COLLAPSING",
    "DIVERGING",
    "DEGENERATE",
    "CONVERGING",
    "DRIFTING",
]

__version__ = "0.2.0"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_PAIRS_GAMMA = 5
_LOG_RANGE_GATE = 0.5
_R2_GATE = 0.5
_SR_METASTABLE_LO = 0.80
_SR_METASTABLE_HI = 1.25
_SR_DEGENERATE = 1.5
_DEGENERATE_COUNT = 3
_HYSTERESIS_COUNT = 3
_MAX_STATE_KEYS = 4
_TOPO_FLOOR = 0.01
_BOOTSTRAP_N = 200
_PERMUTATION_N = 500
_COND_GATE = 1e6
_EMA_ALPHA = 0.3

# Phase labels
INITIALIZING = "INITIALIZING"
METASTABLE = "METASTABLE"
COLLAPSING = "COLLAPSING"
DIVERGING = "DIVERGING"
DEGENERATE = "DEGENERATE"
CONVERGING = "CONVERGING"
DRIFTING = "DRIFTING"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------
class DomainAdapter(Protocol):
    """Interface each NFI subsystem implements."""

    @property
    def domain(self) -> str: ...

    @property
    def state_keys(self) -> list[str]: ...

    def state(self) -> dict[str, float]: ...

    def topo(self) -> float: ...

    def thermo_cost(self) -> float: ...


# ---------------------------------------------------------------------------
# Immutable state snapshot
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NeosynaptexState:
    """Immutable snapshot returned by Neosynaptex.observe().

    Invariant STATE != PROOF: *phi* and *diagnostic* are independent objects.
    Invariant gamma-derived-only: gamma is computed per call, never stored
    on the Neosynaptex instance.
    """

    t: int
    phi: np.ndarray
    phi_per_domain: dict[str, np.ndarray]

    # --- Gamma ---
    gamma_per_domain: dict[str, float]
    gamma_ci_per_domain: dict[str, tuple[float, float]]
    gamma_mean: float
    gamma_std: float
    cross_coherence: float

    # --- Gamma dynamics ---
    dgamma_dt: float
    gamma_ema_per_domain: dict[str, float]

    # --- Universal scaling test ---
    universal_scaling_p: float

    # --- Jacobian ---
    sr_per_domain: dict[str, float]
    cond_per_domain: dict[str, float]
    spectral_radius: float

    # --- Phase ---
    phase: str

    # --- Anomaly isolation ---
    anomaly_score: dict[str, float]

    # --- Granger causality ---
    granger_graph: dict[str, dict[str, float]]

    # --- Phase portrait ---
    portrait: dict[str, float]

    # --- Resilience ---
    resilience_score: float

    # --- Modulation signal ---
    modulation: dict[str, float]

    # --- Full diagnostic ---
    diagnostic: dict

    # --- Internal value function (X8 v2) ---
    value_estimate: ValueEstimate | None = None

    class _Cfg:
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Circular buffer (O(1) push, pre-allocated)
# ---------------------------------------------------------------------------
class _DomainBuffer:
    """Per-domain circular buffer for state, topo, and cost histories."""

    __slots__ = (
        "domain",
        "n",
        "capacity",
        "_state_buf",
        "_topo_buf",
        "_cost_buf",
        "_idx",
        "_full",
        "_total",
    )

    def __init__(self, domain: str, n: int, capacity: int) -> None:
        self.domain = domain
        self.n = n
        self.capacity = capacity
        self._state_buf = np.full((capacity, n), np.nan, dtype=np.float64)
        self._topo_buf = np.full(capacity, np.nan, dtype=np.float64)
        self._cost_buf = np.full(capacity, np.nan, dtype=np.float64)
        self._idx = 0
        self._full = False
        self._total = 0

    def push(self, state_vec: np.ndarray, topo: float, cost: float) -> None:
        """Append one observation. O(1)."""
        self._state_buf[self._idx] = state_vec
        self._topo_buf[self._idx] = topo
        self._cost_buf[self._idx] = cost
        self._idx = (self._idx + 1) % self.capacity
        if not self._full and self._idx == 0:
            self._full = True
        self._total += 1

    @property
    def count(self) -> int:
        return self._total

    @property
    def length(self) -> int:
        """Number of valid entries in the buffer."""
        return self.capacity if self._full else self._idx

    def _ordered(self, buf: np.ndarray) -> np.ndarray:
        """Return buffer contents in chronological order."""
        n = self.length
        if self._full:
            return np.concatenate([buf[self._idx :], buf[: self._idx]])
        return buf[:n].copy()

    def states_array(self) -> np.ndarray:
        return self._ordered(self._state_buf)

    def topos(self) -> np.ndarray:
        return self._ordered(self._topo_buf)

    def costs(self) -> np.ndarray:
        return self._ordered(self._cost_buf)

    def clear(self) -> None:
        self._state_buf[:] = np.nan
        self._topo_buf[:] = np.nan
        self._cost_buf[:] = np.nan
        self._idx = 0
        self._full = False
        self._total = 0


# ---------------------------------------------------------------------------
# Jacobian helper
# ---------------------------------------------------------------------------
def _per_domain_jacobian(states: np.ndarray) -> tuple[float, float]:
    """Estimate spectral radius and condition number from per-domain state history.

    Formula:
        dPhi(t) = Phi(t+1) - Phi(t)
        J_local = lstsq(Phi_prev, dPhi).T
        A_transition = J_local + I
        sr = max |eigenvalues(A_transition)|
        cond = condition_number(Phi_prev)

    Returns:
        (spectral_radius, condition_number) or (NaN, NaN).
    """
    nan_pair = (float("nan"), float("nan"))
    mask = np.all(np.isfinite(states), axis=1)
    clean = states[mask]
    n = states.shape[1]
    if clean.shape[0] < n + 3:
        return nan_pair

    d_phi = np.diff(clean, axis=0)
    phi_prev = clean[:-1]
    x = phi_prev[:-1]
    y = d_phi[1:]

    if x.shape[0] <= n + 1:
        return nan_pair

    cond = float(np.linalg.cond(x))
    if cond > _COND_GATE:
        return nan_pair

    try:
        j_t, _, _, _ = scipy_lstsq(x, y)
        a_transition = j_t.T + np.eye(n)
        eigvals = np.linalg.eigvals(a_transition)
        sr = float(np.max(np.abs(eigvals)))
        return (sr, cond)
    except Exception:
        return nan_pair


# ---------------------------------------------------------------------------
# Gamma helper with bootstrap CI
# ---------------------------------------------------------------------------
def _per_domain_gamma(
    topos: np.ndarray, costs: np.ndarray, seed: int = 0
) -> tuple[float, float, float, float]:
    """Estimate gamma scaling exponent with bootstrap confidence interval.

    Formula:
        C ~ topo^(-gamma)
        gamma = -slope from theilslopes(log(C), log(topo))
        CI from bootstrap resampling (200 iterations, 2.5%-97.5% percentile)

    Gates:
        1. Need >= 5 valid pairs
        2. range(log(topo)) >= 0.5
        3. R^2 >= 0.5

    Returns:
        (gamma, r_squared, ci_low, ci_high) or (NaN, NaN, NaN, NaN).
    """
    nan_quad = (float("nan"), float("nan"), float("nan"), float("nan"))
    valid = np.isfinite(topos) & np.isfinite(costs) & (topos > 0) & (costs > 0)
    t_valid = topos[valid]
    c_valid = costs[valid]

    if len(t_valid) < _MIN_PAIRS_GAMMA:
        return nan_quad

    log_t = np.log(t_valid)
    log_c = np.log(c_valid)

    if np.ptp(log_t) < _LOG_RANGE_GATE:
        return nan_quad

    slope, intercept, _, _ = theilslopes(log_c, log_t)
    gamma = -slope

    yhat = slope * log_t + intercept
    ss_res = np.sum((log_c - yhat) ** 2)
    ss_tot = np.sum((log_c - np.mean(log_c)) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0

    if r_squared < _R2_GATE:
        return nan_quad

    # Bootstrap CI
    rng = np.random.default_rng(seed)
    n_pts = len(log_t)
    boot_gammas = np.empty(_BOOTSTRAP_N)
    for i in range(_BOOTSTRAP_N):
        idx = rng.integers(0, n_pts, n_pts)
        s, _, _, _ = theilslopes(log_c[idx], log_t[idx])
        boot_gammas[i] = -s
    ci_low = float(np.percentile(boot_gammas, 2.5))
    ci_high = float(np.percentile(boot_gammas, 97.5))

    return (float(gamma), float(r_squared), ci_low, ci_high)


# ---------------------------------------------------------------------------
# Permutation test for universal scaling
# ---------------------------------------------------------------------------
def _permutation_test_universal(gamma_bootstraps: dict[str, np.ndarray], seed: int = 0) -> float:
    """Test H0: all domains share the same gamma.

    Uses permutation of bootstrap distributions. Returns p-value.
    High p (>0.05) = fail to reject universal scaling.
    """
    domains = [k for k, v in gamma_bootstraps.items() if len(v) > 0]
    if len(domains) < 2:
        return float("nan")

    all_vals = [gamma_bootstraps[d] for d in domains]
    sizes = [len(v) for v in all_vals]
    pooled = np.concatenate(all_vals)

    # Observed test statistic: variance of group means
    observed_means = np.array([v.mean() for v in all_vals])
    observed_stat = np.var(observed_means)

    rng = np.random.default_rng(seed)
    count_ge = 0
    for _ in range(_PERMUTATION_N):
        perm = rng.permutation(pooled)
        groups = np.split(perm, np.cumsum(sizes[:-1]))
        perm_means = np.array([g.mean() for g in groups])
        if np.var(perm_means) >= observed_stat:
            count_ge += 1

    return float((count_ge + 1) / (_PERMUTATION_N + 1))


# ---------------------------------------------------------------------------
# Granger causality (pairwise, lag-1)
# ---------------------------------------------------------------------------
def _granger_causality(
    gamma_history: dict[str, list[float]], min_len: int = 10
) -> dict[str, dict[str, float]]:
    """Pairwise Granger causality F-statistic between domain gamma series.

    For each pair (i, j): does gamma_i(t-1) improve prediction of gamma_j(t)
    beyond gamma_j(t-1) alone?

    Returns dict[source][target] = F-statistic. Higher F = stronger causal link.
    """
    graph: dict[str, dict[str, float]] = {}
    domains = sorted(gamma_history.keys())

    for source in domains:
        graph[source] = {}
        s_vals = np.array(gamma_history[source])
        for target in domains:
            if source == target:
                continue
            t_vals = np.array(gamma_history[target])
            n = min(len(s_vals), len(t_vals))
            if n < min_len:
                graph[source][target] = float("nan")
                continue

            s = s_vals[-n:]
            t = t_vals[-n:]
            # Skip if too many NaN
            valid = np.isfinite(s[:-1]) & np.isfinite(t[:-1]) & np.isfinite(t[1:])
            if valid.sum() < min_len - 2:
                graph[source][target] = float("nan")
                continue

            y = t[1:][valid]
            x_restricted = t[:-1][valid].reshape(-1, 1)
            x_full = np.column_stack([t[:-1][valid], s[:-1][valid]])

            # Restricted model: y ~ t_lag
            try:
                b_r, _, _, _ = scipy_lstsq(x_restricted, y)
                rss_r = float(np.sum((y - x_restricted @ b_r) ** 2))
            except Exception:
                graph[source][target] = float("nan")
                continue

            # Full model: y ~ t_lag + s_lag
            try:
                b_f, _, _, _ = scipy_lstsq(x_full, y)
                rss_f = float(np.sum((y - x_full @ b_f) ** 2))
            except Exception:
                graph[source][target] = float("nan")
                continue

            n_obs = len(y)
            p_full = 2
            p_restricted = 1
            df1 = p_full - p_restricted
            df2 = n_obs - p_full
            if df2 <= 0 or rss_f < 1e-15:
                graph[source][target] = float("nan")
                continue

            f_stat = ((rss_r - rss_f) / df1) / (rss_f / df2)
            graph[source][target] = round(float(f_stat), 4)

    return graph


# ---------------------------------------------------------------------------
# Anomaly isolation (leave-one-out)
# ---------------------------------------------------------------------------
def _anomaly_isolation(gamma_per_domain: dict[str, float]) -> dict[str, float]:
    """Leave-one-out coherence test. Score = how much coherence improves without domain d.

    anomaly_score near 1.0 = domain d is the outlier dragging coherence down.
    anomaly_score near 0.0 = domain d is consistent with the group.
    """
    scores: dict[str, float] = {}
    valid = {k: v for k, v in gamma_per_domain.items() if np.isfinite(v)}

    if len(valid) < 3:
        return {k: float("nan") for k in gamma_per_domain}

    vals = np.array(list(valid.values()))
    full_cv = np.std(vals) / abs(np.mean(vals)) if abs(np.mean(vals)) > 1e-10 else 0.0
    full_coherence = 1.0 - full_cv

    for d in gamma_per_domain:
        if d not in valid:
            scores[d] = float("nan")
            continue
        remaining = np.array([v for k, v in valid.items() if k != d])
        if len(remaining) < 2:
            scores[d] = float("nan")
            continue
        loo_cv = (
            np.std(remaining) / abs(np.mean(remaining)) if abs(np.mean(remaining)) > 1e-10 else 0.0
        )
        loo_coherence = 1.0 - loo_cv
        improvement = loo_coherence - full_coherence
        scores[d] = round(
            float(max(0.0, min(1.0, improvement / max(1.0 - full_coherence, 1e-6)))), 4
        )

    return scores


# ---------------------------------------------------------------------------
# Phase portrait
# ---------------------------------------------------------------------------
def _phase_portrait(gamma_trace: list[float], sr_trace: list[float]) -> dict[str, float]:
    """Compute phase portrait metrics from (gamma, sr) trajectory.

    - area: convex hull area (small = fixed point, large = wandering)
    - recurrence: fraction of points within epsilon of a previous point
    - distance_to_ideal: mean distance to (1.0, 1.0)
    """
    valid_pairs = [
        (g, s) for g, s in zip(gamma_trace, sr_trace) if np.isfinite(g) and np.isfinite(s)
    ]
    if len(valid_pairs) < 4:
        return {"area": float("nan"), "recurrence": float("nan"), "distance_to_ideal": float("nan")}

    pts = np.array(valid_pairs)

    # Convex hull area
    try:
        hull = ConvexHull(pts)
        area = float(hull.volume)  # 2D: volume = area
    except Exception:
        area = 0.0

    # Recurrence rate (epsilon = 0.05)
    eps = 0.05
    n = len(pts)
    recurrence_count = 0
    for i in range(1, n):
        for j in range(i):
            if np.linalg.norm(pts[i] - pts[j]) < eps:
                recurrence_count += 1
                break
    recurrence = float(recurrence_count / max(n - 1, 1))

    # Distance to ideal (1.0, 1.0)
    ideal = np.array([1.0, 1.0])
    distances = np.linalg.norm(pts - ideal, axis=1)
    distance_to_ideal = float(np.mean(distances))

    return {
        "area": round(area, 6),
        "recurrence": round(recurrence, 4),
        "distance_to_ideal": round(distance_to_ideal, 4),
    }


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class Neosynaptex:
    """Integrating mirror layer for NFI.

    Observes registered domain adapters and computes:
    - Per-domain gamma with bootstrap CI and Theil-Sen regression
    - Per-domain spectral radius with condition number gating
    - Cross-domain coherence and permutation test of universal scaling
    - Granger causality graph between domains
    - Anomaly isolation (leave-one-out)
    - Phase portrait topology (area, recurrence, distance-to-ideal)
    - Resilience score (return rate after departures from metastability)
    - Reflexive modulation signal (bounded |mod| <= 0.05)
    - Phase with hysteresis (CONVERGING / METASTABLE / DRIFTING / ...)

    Usage::

        nx = Neosynaptex(window=16)
        nx.register(MockBnSynAdapter())
        nx.register(MockMfnAdapter())
        state = nx.observe()
        print(state.phase, state.gamma_mean, state.modulation)
    """

    def __init__(self, window: int = 16) -> None:
        if window < 8:
            raise ValueError(f"window must be >= 8, got {window}")
        self._window = window
        self._adapters: dict[str, DomainAdapter] = {}
        self._buffers: dict[str, _DomainBuffer] = {}
        self._tick = 0

        # Phase hysteresis
        self._confirmed_phase = INITIALIZING
        self._candidate_phase = INITIALIZING
        self._candidate_count = 0
        self._degenerate_count = 0

        # History
        self._history: list[NeosynaptexState] = []
        self._gamma_history: dict[str, list[float]] = {}
        self._gamma_trace: list[float] = []
        self._sr_trace: list[float] = []

        # EMA state
        self._gamma_ema: dict[str, float] = {}

        # Resilience tracking
        self._departures = 0
        self._returns = 0
        self._was_metastable = False

        # Bootstrap cache for permutation test
        self._gamma_bootstraps: dict[str, np.ndarray] = {}

        # Free-energy proxy history for valence (X8 v2)
        self._f_history: list[float] = []

    def register(self, adapter: DomainAdapter) -> None:
        """Register a domain adapter. Max 4 state variables per adapter."""
        keys = adapter.state_keys
        if len(keys) > _MAX_STATE_KEYS:
            raise ValueError(
                f"Adapter '{adapter.domain}' has {len(keys)} state keys, max is {_MAX_STATE_KEYS}"
            )
        name = adapter.domain
        if name in self._adapters:
            raise ValueError(f"Domain '{name}' already registered")
        self._adapters[name] = adapter
        self._buffers[name] = _DomainBuffer(name, len(keys), self._window)
        self._gamma_history[name] = []
        self._gamma_ema[name] = float("nan")

    def observe(self) -> NeosynaptexState:
        """Collect state from all adapters, compute full diagnostics.

        Returns immutable NeosynaptexState with gamma CI, Granger causality,
        anomaly isolation, phase portrait, resilience, and modulation signal.
        """
        if not self._adapters:
            raise RuntimeError("No adapters registered. Call register() first.")

        self._tick += 1
        domain_order = sorted(self._adapters.keys())

        # === Layer 1: Collect ===
        phi_parts: list[np.ndarray] = []
        phi_per_domain: dict[str, np.ndarray] = {}

        for name in domain_order:
            adapter = self._adapters[name]
            buf = self._buffers[name]
            s = adapter.state()
            vec = np.array([s.get(k, float("nan")) for k in adapter.state_keys], dtype=np.float64)
            t_val = adapter.topo()
            c_val = adapter.thermo_cost()
            if np.isfinite(t_val) and t_val < _TOPO_FLOOR:
                t_val = _TOPO_FLOOR
            if np.isfinite(c_val) and c_val < _TOPO_FLOOR:
                c_val = _TOPO_FLOOR
            buf.push(vec, t_val, c_val)
            phi_parts.append(vec.copy())
            phi_per_domain[name] = vec.copy()

        phi = np.concatenate(phi_parts)

        # === Layer 2: Per-domain Jacobian with condition number ===
        sr_per_domain: dict[str, float] = {}
        cond_per_domain: dict[str, float] = {}

        for name in domain_order:
            buf = self._buffers[name]
            if buf.length < buf.n + 3:
                sr_per_domain[name] = float("nan")
                cond_per_domain[name] = float("nan")
            else:
                sr, cond = _per_domain_jacobian(buf.states_array())
                sr_per_domain[name] = sr
                cond_per_domain[name] = cond

        sr_valid = [v for v in sr_per_domain.values() if np.isfinite(v)]
        spectral_radius = float(np.median(sr_valid)) if sr_valid else float("nan")

        # === Layer 3: Per-domain gamma with bootstrap CI ===
        gamma_per_domain: dict[str, float] = {}
        gamma_ci_per_domain: dict[str, tuple[float, float]] = {}
        r2_per_domain: dict[str, float] = {}

        for i, name in enumerate(domain_order):
            buf = self._buffers[name]
            g, r2, ci_lo, ci_hi = _per_domain_gamma(
                buf.topos(), buf.costs(), seed=self._tick * 100 + i
            )
            gamma_per_domain[name] = g
            gamma_ci_per_domain[name] = (ci_lo, ci_hi)
            r2_per_domain[name] = r2
            self._gamma_history[name].append(g)

            # Bootstrap cache
            if np.isfinite(g):
                rng = np.random.default_rng(self._tick * 100 + i)
                topos = buf.topos()
                costs = buf.costs()
                valid = np.isfinite(topos) & np.isfinite(costs) & (topos > 0) & (costs > 0)
                lt = np.log(topos[valid])
                lc = np.log(costs[valid])
                n_pts = len(lt)
                boot = np.empty(_BOOTSTRAP_N)
                for b in range(_BOOTSTRAP_N):
                    idx = rng.integers(0, n_pts, n_pts)
                    s, _, _, _ = theilslopes(lc[idx], lt[idx])
                    boot[b] = -s
                self._gamma_bootstraps[name] = boot
            else:
                self._gamma_bootstraps[name] = np.array([])

            # EMA
            if np.isfinite(g):
                prev = self._gamma_ema[name]
                if np.isfinite(prev):
                    self._gamma_ema[name] = _EMA_ALPHA * g + (1 - _EMA_ALPHA) * prev
                else:
                    self._gamma_ema[name] = g

        gamma_ema_per_domain = dict(self._gamma_ema)

        # Cross-domain coherence
        gamma_valid = [v for v in gamma_per_domain.values() if np.isfinite(v)]
        if len(gamma_valid) >= 2:
            gamma_mean = float(np.mean(gamma_valid))
            gamma_std = float(np.std(gamma_valid))
            cross_coherence = (
                1.0 - gamma_std / gamma_mean if abs(gamma_mean) > 1e-10 else float("nan")
            )
        elif len(gamma_valid) == 1:
            gamma_mean = gamma_valid[0]
            gamma_std = float("nan")
            cross_coherence = float("nan")
        else:
            gamma_mean = float("nan")
            gamma_std = float("nan")
            cross_coherence = float("nan")

        # === dg/dt: gamma convergence rate ===
        self._gamma_trace.append(gamma_mean)
        self._sr_trace.append(spectral_radius)
        dgamma_dt = float("nan")
        if len(self._gamma_trace) >= 5:
            recent = [g for g in self._gamma_trace[-self._window :] if np.isfinite(g)]
            if len(recent) >= 5:
                x_t = np.arange(len(recent), dtype=np.float64)
                slope_g, _, _, _ = theilslopes(recent, x_t)
                dgamma_dt = float(slope_g)

        # === Permutation test for universal scaling ===
        universal_scaling_p = _permutation_test_universal(self._gamma_bootstraps, seed=self._tick)

        # === Granger causality ===
        granger_graph = _granger_causality(self._gamma_history)

        # === Anomaly isolation ===
        anomaly_score = _anomaly_isolation(gamma_per_domain)

        # === Phase portrait ===
        portrait = _phase_portrait(self._gamma_trace, self._sr_trace)

        # === Phase determination with hysteresis ===
        raw_phase = self._raw_phase(spectral_radius, dgamma_dt, gamma_mean)

        if raw_phase == self._confirmed_phase:
            self._candidate_phase = raw_phase
            self._candidate_count = 0
        elif raw_phase == self._candidate_phase:
            self._candidate_count += 1
            if self._candidate_count >= _HYSTERESIS_COUNT:
                self._confirmed_phase = raw_phase
                self._candidate_count = 0
        else:
            self._candidate_phase = raw_phase
            self._candidate_count = 1

        phase = self._confirmed_phase

        # === Resilience tracking ===
        is_meta = phase == METASTABLE
        if self._was_metastable and not is_meta:
            self._departures += 1
        if not self._was_metastable and is_meta and self._departures > 0:
            self._returns += 1
        self._was_metastable = is_meta
        resilience_score = (
            float(self._returns / self._departures) if self._departures > 0 else float("nan")
        )

        # === Reflexive modulation signal ===
        modulation: dict[str, float] = {}
        gamma_target = 1.0
        alpha_mod = 0.05
        for name in domain_order:
            g = gamma_per_domain[name]
            dg = dgamma_dt
            if np.isfinite(g) and np.isfinite(dg):
                raw_mod = (
                    -alpha_mod * (g - gamma_target) * (1.0 if dg > 0 else -1.0 if dg < 0 else 0.0)
                )
                modulation[name] = round(float(np.clip(raw_mod, -0.05, 0.05)), 6)
            else:
                modulation[name] = 0.0

        # === Value function (X8 v2: 4-signal neuromodulatory) ===
        f_proxy = 1.0 - cross_coherence if np.isfinite(cross_coherence) else 0.5
        self._f_history.append(f_proxy)
        if len(self._f_history) > 10:
            self._f_history = self._f_history[-10:]

        gamma_valid_count = len(gamma_valid)
        n_total_domains = len(domain_order)
        if phase != INITIALIZING and gamma_valid_count > 0 and np.isfinite(gamma_mean):
            value_estimate = estimate_value(
                gamma_mean=gamma_mean,
                spectral_radius=spectral_radius if np.isfinite(spectral_radius) else 1.0,
                cross_coherence=cross_coherence if np.isfinite(cross_coherence) else 0.0,
                n_valid_domains=gamma_valid_count,
                n_total_domains=max(n_total_domains, 1),
                f_history=self._f_history,
            )
        else:
            value_estimate = None

        # === Build diagnostic ===
        diagnostic = {
            "tick": self._tick,
            "sr_per_domain": dict(sr_per_domain),
            "cond_per_domain": dict(cond_per_domain),
            "gamma_per_domain": dict(gamma_per_domain),
            "gamma_ci_per_domain": {k: list(v) for k, v in gamma_ci_per_domain.items()},
            "r2_per_domain": dict(r2_per_domain),
            "n_gamma_valid": len(gamma_valid),
            "dgamma_dt": dgamma_dt,
            "universal_scaling_p": universal_scaling_p,
            "degenerate_count": self._degenerate_count,
            "resilience": {"departures": self._departures, "returns": self._returns},
        }

        state = NeosynaptexState(
            t=self._tick,
            phi=phi.copy(),
            phi_per_domain={k: v.copy() for k, v in phi_per_domain.items()},
            gamma_per_domain=dict(gamma_per_domain),
            gamma_ci_per_domain=dict(gamma_ci_per_domain),
            gamma_mean=gamma_mean,
            gamma_std=gamma_std,
            cross_coherence=cross_coherence,
            dgamma_dt=dgamma_dt,
            gamma_ema_per_domain=dict(gamma_ema_per_domain),
            universal_scaling_p=universal_scaling_p,
            sr_per_domain=dict(sr_per_domain),
            cond_per_domain=dict(cond_per_domain),
            spectral_radius=spectral_radius,
            phase=phase,
            anomaly_score=dict(anomaly_score),
            granger_graph=dict(granger_graph),
            portrait=dict(portrait),
            resilience_score=resilience_score,
            modulation=dict(modulation),
            diagnostic=dict(diagnostic),
            value_estimate=value_estimate,
        )

        self._history.append(state)
        max_hist = 3 * self._window
        if len(self._history) > max_hist:
            self._history = self._history[-max_hist:]

        return state

    def _raw_phase(self, sr: float, dgamma_dt: float, gamma_mean: float) -> str:
        """Determine raw phase before hysteresis.

        Phase logic:
            NaN sr                      -> INITIALIZING
            sr > 1.5 sustained (3+)     -> DEGENERATE
            sr > 1.25                   -> DIVERGING
            sr < 0.80                   -> COLLAPSING
            |gamma-1| < 0.15 and dg->0  -> METASTABLE
            dg < -0.005 toward 1.0      -> CONVERGING
            dg > 0.005 away from 1.0    -> DRIFTING
            else                        -> METASTABLE
        """
        if not np.isfinite(sr):
            self._degenerate_count = 0
            return INITIALIZING

        if sr > _SR_DEGENERATE:
            self._degenerate_count += 1
            if self._degenerate_count >= _DEGENERATE_COUNT:
                return DEGENERATE
            return DIVERGING
        else:
            self._degenerate_count = 0

        if sr > _SR_METASTABLE_HI:
            return DIVERGING
        if sr < _SR_METASTABLE_LO:
            return COLLAPSING

        # SR is in metastable band -- check gamma dynamics
        if np.isfinite(dgamma_dt) and np.isfinite(gamma_mean):
            dist_from_one = gamma_mean - 1.0
            moving_toward = (dist_from_one > 0 and dgamma_dt < -0.003) or (
                dist_from_one < 0 and dgamma_dt > 0.003
            )
            moving_away = (dist_from_one > 0 and dgamma_dt > 0.005) or (
                dist_from_one < 0 and dgamma_dt < -0.005
            )

            if moving_toward and abs(dist_from_one) > 0.05:
                return CONVERGING
            if moving_away and abs(dist_from_one) > 0.05:
                return DRIFTING

        return METASTABLE

    def need_vector(self) -> None:
        """Placeholder for v2. Returns None."""
        return None

    def history(self) -> list[NeosynaptexState]:
        """Return list of past snapshots (oldest first)."""
        return list(self._history)

    def reset(self) -> None:
        """Clear all state history."""
        for buf in self._buffers.values():
            buf.clear()
        self._history.clear()
        self._gamma_history = {k: [] for k in self._gamma_history}
        self._gamma_trace.clear()
        self._sr_trace.clear()
        self._gamma_ema = {k: float("nan") for k in self._gamma_ema}
        self._gamma_bootstraps = {k: np.array([]) for k in self._gamma_bootstraps}
        self._tick = 0
        self._degenerate_count = 0
        self._confirmed_phase = INITIALIZING
        self._candidate_phase = INITIALIZING
        self._candidate_count = 0
        self._departures = 0
        self._returns = 0
        self._was_metastable = False
        self._f_history.clear()

    def export_proof(self, path: str | None = None) -> dict:
        """Export proof bundle as JSON-serializable dict.

        Contains all evidence: gamma values, CIs, R^2, spectral radii,
        condition numbers, Granger graph, anomaly scores, phase portrait,
        resilience, and verdict.
        """
        if not self._history:
            return {"error": "no observations"}
        s = self._history[-1]
        proof = {
            "version": __version__,
            "ticks": s.t,
            "gamma": {
                "per_domain": {
                    k: {
                        "value": round(v, 4) if np.isfinite(v) else None,
                        "ci": [
                            round(c, 4) if np.isfinite(c) else None
                            for c in s.gamma_ci_per_domain[k]
                        ],
                        "r2": round(s.diagnostic["r2_per_domain"][k], 4)
                        if np.isfinite(s.diagnostic["r2_per_domain"].get(k, float("nan")))
                        else None,
                        "ema": round(s.gamma_ema_per_domain.get(k, float("nan")), 4)
                        if np.isfinite(s.gamma_ema_per_domain.get(k, float("nan")))
                        else None,
                    }
                    for k, v in s.gamma_per_domain.items()
                },
                "mean": round(s.gamma_mean, 4) if np.isfinite(s.gamma_mean) else None,
                "std": round(s.gamma_std, 4) if np.isfinite(s.gamma_std) else None,
                "dgamma_dt": round(s.dgamma_dt, 6) if np.isfinite(s.dgamma_dt) else None,
                "universal_scaling_p": round(s.universal_scaling_p, 4)
                if np.isfinite(s.universal_scaling_p)
                else None,
            },
            "jacobian": {
                k: {
                    "sr": round(sr, 4) if np.isfinite(sr) else None,
                    "cond": round(s.cond_per_domain.get(k, float("nan")), 2)
                    if np.isfinite(s.cond_per_domain.get(k, float("nan")))
                    else None,
                }
                for k, sr in s.sr_per_domain.items()
            },
            "phase": s.phase,
            "anomaly": {k: v if np.isfinite(v) else None for k, v in s.anomaly_score.items()},
            "granger": {
                src: {tgt: v if np.isfinite(v) else None for tgt, v in targets.items()}
                for src, targets in s.granger_graph.items()
            },
            "portrait": {k: v if np.isfinite(v) else None for k, v in s.portrait.items()},
            "resilience": round(s.resilience_score, 4) if np.isfinite(s.resilience_score) else None,
            "modulation": {k: v for k, v in s.modulation.items()},
            "coherence": round(s.cross_coherence, 4) if np.isfinite(s.cross_coherence) else None,
            "verdict": "COHERENT"
            if (
                np.isfinite(s.cross_coherence)
                and s.cross_coherence > 0.85
                and s.phase in (METASTABLE, CONVERGING)
            )
            else "INCOHERENT"
            if s.phase in (DEGENERATE, DIVERGING)
            else "PARTIAL",
        }

        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(proof, f, indent=2, ensure_ascii=False)
        return proof


# ---------------------------------------------------------------------------
# Mock Adapters
# ---------------------------------------------------------------------------
class MockBnSynAdapter:
    """Mock BN-Syn: oscillating near criticality with gamma ~ 0.95.

    topo = 1.0 + 8.0 * |sin(0.2t)|
    cost = 8.0 * topo^(-0.95) + noise   (gamma=0.95 by construction)
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self) -> str:
        return "spike"

    @property
    def state_keys(self) -> list[str]:
        return ["sigma", "firing_rate", "coherence"]

    def state(self) -> dict[str, float]:
        self._t += 1
        t = self._t
        return {
            "sigma": 1.0 + 0.15 * math.sin(0.1 * t) + self._rng.normal(0, 0.02),
            "firing_rate": 20.0 + 5.0 * math.sin(0.08 * t) + self._rng.normal(0, 0.5),
            "coherence": 0.7 + 0.1 * math.cos(0.12 * t) + self._rng.normal(0, 0.02),
        }

    def topo(self) -> float:
        self._topo = max(_TOPO_FLOOR, 1.0 + 8.0 * abs(math.sin(0.2 * self._t)))
        return self._topo

    def thermo_cost(self) -> float:
        t = getattr(self, "_topo", 5.0)
        return max(_TOPO_FLOOR, 8.0 * t ** (-0.95) + self._rng.normal(0, 0.03))


class MockMfnAdapter:
    """Mock MFN+: morphogenesis with gamma ~ 1.0.

    topo_base = 1.0 + 10.0 * |sin(0.2t)|
    cost = 10.0 * topo^(-1.0) + noise   (gamma=1.0 by construction)
    """

    def __init__(self, seed: int = 43) -> None:
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self) -> str:
        return "morpho"

    @property
    def state_keys(self) -> list[str]:
        return ["d_box", "beta0", "beta1", "delta_h"]

    def state(self) -> dict[str, float]:
        self._t += 1
        t = self._t
        tb = max(0.5, 1.0 + 10.0 * abs(math.sin(0.2 * t)))
        self._topo_base = tb
        self._delta_h = max(_TOPO_FLOOR, 10.0 * tb ** (-1.0) + self._rng.normal(0, 0.05))
        return {
            "d_box": 1.7 + 0.1 * math.sin(0.04 * t),
            "beta0": tb * 0.6,
            "beta1": tb * 0.4,
            "delta_h": self._delta_h,
        }

    def topo(self) -> float:
        return max(_TOPO_FLOOR, self._topo_base)

    def thermo_cost(self) -> float:
        return self._delta_h


class MockPsycheCoreAdapter:
    """Mock PsycheCore: free energy minimization with gamma ~ 1.05.

    topo = 5.0 + 45.0 * |sin(0.2t)|
    cost = 20.0 * topo^(-1.05) + noise
    """

    def __init__(self, seed: int = 44) -> None:
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self) -> str:
        return "psyche"

    @property
    def state_keys(self) -> list[str]:
        return ["free_energy", "kuramoto_r"]

    def state(self) -> dict[str, float]:
        self._t += 1
        t = self._t
        return {
            "free_energy": max(0.1, 5.0 * math.exp(-0.02 * t) + self._rng.normal(0, 0.1)),
            "kuramoto_r": 0.8 + 0.1 * math.sin(0.07 * t) + self._rng.normal(0, 0.02),
        }

    def topo(self) -> float:
        self._topo = max(_TOPO_FLOOR, 5.0 + 45.0 * abs(math.sin(0.2 * self._t)))
        return self._topo

    def thermo_cost(self) -> float:
        t = getattr(self, "_topo", 25.0)
        return max(_TOPO_FLOOR, 20.0 * t ** (-1.05) + self._rng.normal(0, 0.02))


class MockMarketAdapter:
    """Mock mvstack/GeoSync: regime dynamics with gamma ~ 1.08.

    topo = 1.0 + 7.0 * |sin(0.2t)|
    cost = 5.0 * topo^(-1.08) + noise
    """

    def __init__(self, seed: int = 45) -> None:
        self._rng = np.random.default_rng(seed)
        self._t = 0

    @property
    def domain(self) -> str:
        return "market"

    @property
    def state_keys(self) -> list[str]:
        return ["regime", "w1_distance", "ricci_curvature"]

    def state(self) -> dict[str, float]:
        self._t += 1
        t = self._t
        return {
            "regime": 1.0 if math.sin(0.06 * t) > 0 else 0.0,
            "w1_distance": 0.5 + 0.3 * abs(math.sin(0.09 * t)) + self._rng.normal(0, 0.02),
            "ricci_curvature": -0.2 + 0.4 * math.sin(0.05 * t) + self._rng.normal(0, 0.03),
        }

    def topo(self) -> float:
        self._topo = max(_TOPO_FLOOR, 1.0 + 7.0 * abs(math.sin(0.2 * self._t)))
        return self._topo

    def thermo_cost(self) -> float:
        t = getattr(self, "_topo", 4.0)
        return max(_TOPO_FLOOR, 5.0 * t ** (-1.08) + self._rng.normal(0, 0.02))
