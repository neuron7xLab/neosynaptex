"""Phase 2 — adapter fixes for long runs.

Two new adapter classes guarantee:
    * no modulo cycling of historical data (spec §Fix 1)
    * explicit exhaustion — raise IndexError instead of silently wrapping
    * deterministic pre-load of enough internal state to satisfy the
      requested tick budget before the first γ read

Neither class mutates the original substrate adapters. Both conform to
the DomainAdapter Protocol (domain/state_keys/state/topo/thermo_cost).
"""

from __future__ import annotations

import math

import numpy as np

from substrates.geosync_market.adapter import GeoSyncMarketAdapter

__all__ = [
    "LinearBnSynAdapter",
    "LinearGeoSyncAdapter",
    "SeriesExhausted",
]


class SeriesExhausted(IndexError):
    """Raised when a linear adapter runs past its pre-loaded history."""


# ── BN-Syn linear adapter ──────────────────────────────────────────────


_BNSYN_WINDOW = 50
_BNSYN_STEPS_PER_TICK = 20
_BNSYN_P_SPONTANEOUS = 0.002
_BNSYN_INIT_ACTIVE = 5


class LinearBnSynAdapter:
    """BnSyn critical-branching network with a linear (non-wrapping) cursor.

    Rebuilt from the same physics as :class:`BnSynAdapter` but with:
      * configurable `sim_steps` so 2000+ logged ticks fit without reuse
      * a strictly linear cursor — `state()` raises ``SeriesExhausted``
        once the pre-computed history runs out instead of modulo-cycling
      * an explicit ``burn_in(n)`` helper that advances the cursor
        without emitting data (used for the Phase 3 warmup)
    """

    def __init__(
        self,
        seed: int = 42,
        N: int = 200,
        k: int = 10,
        sim_steps: int = 50_000,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self._N = N
        self._k = k
        self._p_transmit = 1.0 / k
        self._window = _BNSYN_WINDOW
        self._sim_steps = int(sim_steps)

        # Build sparse connectivity (same shape as upstream).
        self._targets: list[np.ndarray] = []
        for i in range(N):
            pool = np.delete(np.arange(N), i)
            targets = self._rng.choice(pool, size=min(k, N - 1), replace=False)
            self._targets.append(targets)

        self._pop_rates = self._simulate(self._sim_steps)
        self._t = 0  # linear cursor in internal sim-step units

    # DomainAdapter interface ───────────────────────────────────────────

    @property
    def domain(self) -> str:
        return "spike"

    @property
    def state_keys(self) -> list[str]:
        return ["firing_rate", "rate_cv", "branching_ratio"]

    def state(self) -> dict[str, float]:
        # Advance cursor by the same amount BnSynAdapter does per tick.
        self._t += _BNSYN_STEPS_PER_TICK
        rate, cv = self._window_stats()
        return {
            "firing_rate": rate,
            "rate_cv": cv,
            "branching_ratio": self._p_transmit * self._k,
        }

    def topo(self) -> float:
        rate, _ = self._window_stats()
        return max(rate, 1e-6)

    def thermo_cost(self) -> float:
        _, cv = self._window_stats()
        return max(cv, 1e-6)

    # Experiment-specific helpers ───────────────────────────────────────

    def burn_in(self, n_ticks: int) -> None:
        """Advance the cursor by `n_ticks` without emitting any reading.

        Equivalent to discarding the first `n_ticks * 20` internal sim
        steps before the logged window begins.
        """
        self._t += n_ticks * _BNSYN_STEPS_PER_TICK
        if self._t + self._window > self._sim_steps:
            raise SeriesExhausted(f"burn_in({n_ticks}) would exceed sim_steps={self._sim_steps}")

    def max_ticks(self) -> int:
        """Upper bound on remaining ticks before exhaustion."""
        available = self._sim_steps - self._window - self._t
        return max(0, available // _BNSYN_STEPS_PER_TICK)

    # Internals ─────────────────────────────────────────────────────────

    def _window_stats(self) -> tuple[float, float]:
        t = self._t
        if t + self._window > self._sim_steps:
            raise SeriesExhausted(
                f"BnSyn cursor {t} + window {self._window} > sim_steps {self._sim_steps}"
            )
        window = self._pop_rates[t : t + self._window]
        mean_rate = float(window.mean())
        if mean_rate < 1e-10:
            return 1e-6, 1.0
        cv = float(window.std() / mean_rate)
        return mean_rate, cv

    def _simulate(self, T: int) -> np.ndarray:
        """Run T steps of critical-branching dynamics; return pop_rate series.

        Physics identical to :class:`BnSynAdapter._simulate` except that T
        is a parameter rather than a module constant so we can size the
        history to fit the tick budget.
        """
        N = self._N
        pop_rate = np.zeros(T, dtype=np.float64)

        conn = np.zeros((N, N), dtype=np.float32)
        for i, tgts in enumerate(self._targets):
            conn[i, tgts] = 1.0

        active = np.zeros(N, dtype=bool)
        active[self._rng.choice(N, size=_BNSYN_INIT_ACTIVE, replace=False)] = True

        for step in range(T):
            pop_rate[step] = float(active.sum()) / N
            if active.any():
                input_strength = conn[active].sum(axis=0)
            else:
                input_strength = np.zeros(N, dtype=np.float32)
            transmit_prob = 1.0 - (1.0 - self._p_transmit) ** input_strength
            next_active = self._rng.random(N) < transmit_prob
            next_active |= self._rng.random(N) < _BNSYN_P_SPONTANEOUS
            next_active &= ~active
            active = next_active
        return pop_rate


# ── GeoSync linear adapter ─────────────────────────────────────────────


class LinearGeoSyncAdapter(GeoSyncMarketAdapter):
    """GeoSync wrapper that forbids modulo cycling of the return history.

    Pulls a large lookback window from yfinance (default 3650 days ≈ 10
    years) so 2000+ daily ticks fit without repetition. Overrides
    :meth:`state` to raise :class:`SeriesExhausted` instead of wrapping.
    """

    def __init__(self, lookback_days: int = 3650) -> None:
        super().__init__(lookback_days=lookback_days)
        self._t = 0  # re-zero (super already does this, kept explicit)

    def max_ticks(self) -> int:
        """Upper bound on remaining ticks before exhaustion."""
        if not self._loaded or self._returns is None:
            self._load()
        if self._returns is None:
            return 0
        n_bars = len(self._returns)
        cursor_start = 60  # _WINDOW in upstream adapter
        available = n_bars - cursor_start
        return max(0, available - self._t)

    def state(self) -> dict[str, float]:
        self._ensure_loaded()

        if not self._loaded or self._returns is None:
            # Same neutral fallback as upstream — analysis layer will
            # mask these via the validity mask anyway.
            return super().state()

        r = self._returns
        n_bars = len(r)
        cursor_start = 60  # _WINDOW upstream

        # Linear cursor — no modulo, no wrap.
        if cursor_start + self._t >= n_bars:
            raise SeriesExhausted(
                f"GeoSync cursor {cursor_start + self._t} >= n_bars {n_bars} "
                f"— requested more ticks than history supports"
            )

        idx = cursor_start + self._t
        self._t += 1

        w_now = r[max(0, idx - 60) : idx]
        if len(w_now) < 20:
            # Insufficient window — use whatever is there.
            w_now = r[:idx] if idx > 0 else r[:1]
        ricci_now, fiedler = self._ricci(w_now)

        w_prev = r[max(0, idx - 61) : idx - 1]
        if len(w_prev) >= 20:
            ricci_prev, _ = self._ricci(w_prev)
        else:
            ricci_prev = ricci_now
        delta_ricci = ricci_now - ricci_prev

        # Rolling history for z-scoring.
        ricci_history: list[float] = []
        delta_history: list[float] = []
        history_start = max(0, idx - 60)
        for i in range(history_start, idx):
            w = r[max(0, i - 60) : i]
            if len(w) >= 20:
                r_i, _ = self._ricci(w)
                ricci_history.append(r_i)
                if len(ricci_history) > 1:
                    delta_history.append(ricci_history[-1] - ricci_history[-2])

        def _zscore(x: float, series: list[float]) -> float:
            if len(series) < 2:
                return 0.0
            mu = float(np.mean(series))
            sd = float(np.std(series))
            return float((x - mu) / sd) if sd > 1e-8 else 0.0

        z_delta = _zscore(delta_ricci, delta_history if delta_history else [delta_ricci])
        z_mean = _zscore(ricci_now, ricci_history if ricci_history else [ricci_now])
        combo = z_delta - 0.5 * z_mean

        stress = max(abs(combo), 1e-6)
        physical_cost = (1.0 + stress) / max(fiedler, 1e-3)

        result = {
            "fiedler_lambda2": fiedler,
            "combo_signal": physical_cost,
            "ricci_mean": ricci_now,
            "delta_ricci": delta_ricci,
        }
        self._cached_state = result
        return result

    def burn_in(self, n_ticks: int) -> None:
        """Advance cursor by `n_ticks` without reading."""
        self._ensure_loaded()
        if self._returns is None:
            return
        if 60 + self._t + n_ticks > len(self._returns):
            raise SeriesExhausted(
                f"GeoSync burn_in({n_ticks}) would exceed history of {len(self._returns)} bars"
            )
        self._t += n_ticks


def verify_no_repetition(series: np.ndarray, tolerance: float = 1e-12) -> bool:
    """True if no contiguous block of length ≥ 4 repeats in `series`.

    A quick guard that catches any lingering modulo cycling — if the
    cursor wraps, some consecutive quadruple of readings will reappear
    later in the series. We test every window of length 4 against every
    later starting position via a hashed rolling sum; this is O(n) and
    detects any exact repetition that a wrap would introduce.
    """
    x = np.asarray(series, dtype=np.float64)
    finite = np.isfinite(x)
    if not finite.all():
        x = x[finite]
    n = len(x)
    if n < 8:
        return True
    w = 4
    seen: dict[tuple[int, ...], int] = {}
    for i in range(n - w + 1):
        key = tuple(int(math.floor(v * 1e9)) for v in x[i : i + w])
        if key in seen and (i - seen[key]) >= w:
            return False
        seen[key] = i
    return True
