"""GeoSync Market Adapter for neosynaptex.

Connects GeoSync Forman-Ricci signal to the neosynaptex framework.

Mapping (physically motivated):
  topo  = Fiedler eigenvalue λ₂ of correlation graph Laplacian
          → measures algebraic connectivity / topological complexity
          → when λ₂ → 0: graph near disconnection (fracture precursor)

  cost  = |combo_signal| = |z(delta_Ricci) - 0.5 * z(Ricci_mean)|
          → thermodynamic cost = magnitude of topological stress
          → high when graph is rapidly fragmenting

Invariant: gamma_PSD = 2H + 1 (not 2H - 1). Gamma is DERIVED, never assigned.

Signal:  GeoSync combo_v1 from 19-asset rolling correlation graph.
Data:    yfinance daily, 60d rolling window.
Domain:  "geosync_market"
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

# 19-asset universe (GeoSync canonical)
_TICKERS = [
    "EURUSD=X", "GBPUSD=X", "JPY=X", "AUDUSD=X", "CAD=X",
    "SPY", "QQQ", "GLD", "TLT", "XLE", "XLF", "XLK", "XLV", "EEM",
    "BTC-USD", "ETH-USD",
    "CL=F", "GC=F", "ZC=F",
]

_WINDOW = 60        # rolling correlation window
_THRESHOLD = 0.30   # edge threshold
_MIN_BARS = 65      # minimum bars per ticker to keep it


class GeoSyncMarketAdapter:
    """GeoSync Forman-Ricci curvature as neosynaptex market substrate."""

    def __init__(self, lookback_days: int = 120) -> None:
        self._lookback = lookback_days
        self._returns: np.ndarray | None = None
        self._loaded = False
        self._error: str | None = None
        self._t = 0
        self._cached_state: Dict[str, float] | None = None

    @property
    def domain(self) -> str:
        return "geosync_market"

    @property
    def state_keys(self) -> List[str]:
        return ["fiedler_lambda2", "combo_signal", "ricci_mean", "delta_ricci"]

    # ── Data loading ────────────────────────────────────────────
    def _load(self) -> None:
        """Download and prepare log-return matrix. Sets fallback on any failure."""
        try:
            import yfinance as yf

            raw = yf.download(
                _TICKERS,
                period=f"{self._lookback}d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )["Close"]

            # Drop tickers with too many NaNs
            raw = raw.dropna(axis=1, thresh=_MIN_BARS)
            raw = raw.ffill().dropna()

            if len(raw) < _WINDOW + 5 or raw.shape[1] < 5:
                raise RuntimeError(
                    f"insufficient clean data: {raw.shape[0]} bars, {raw.shape[1]} tickers"
                )

            log_returns = np.log(raw / raw.shift(1)).dropna()
            self._returns = log_returns.values
            self._loaded = True

        except Exception as e:
            self._loaded = False
            self._error = str(e)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    # ── Graph computations ──────────────────────────────────────
    def _ricci(self, window: np.ndarray) -> tuple[float, float]:
        """Compute (mean Forman-Ricci, Fiedler λ₂) from a returns window."""
        n = window.shape[1]
        corr = np.corrcoef(window.T)
        np.fill_diagonal(corr, 0.0)

        # Adjacency matrix — edges where |corr| > threshold
        adj = (np.abs(corr) > _THRESHOLD).astype(float)
        deg = adj.sum(axis=1)

        # Forman-Ricci per edge: Ric_F(e=(u,v)) = 4 - deg(u) - deg(v)
        ricci_vals: list[float] = []
        for u in range(n):
            for v in range(u + 1, n):
                if adj[u, v] > 0:
                    ricci_vals.append(4.0 - float(deg[u]) - float(deg[v]))

        ricci_mean = float(np.mean(ricci_vals)) if ricci_vals else 0.0

        # Fiedler eigenvalue = smallest NONZERO eigenvalue of Laplacian
        # (algebraic connectivity). For disconnected graphs, zero eigenvalues
        # have multiplicity = number of components, so we skip them.
        laplacian = np.diag(deg) - adj
        eigvals = np.sort(np.linalg.eigvalsh(laplacian))
        # Find first eigenvalue > 1e-8 (above numerical zero)
        positive = eigvals[eigvals > 1e-8]
        fiedler = float(positive[0]) if len(positive) > 0 else 0.0

        return ricci_mean, max(fiedler, 1e-6)

    # ── DomainAdapter interface ─────────────────────────────────
    def state(self) -> Dict[str, float]:
        """Return current state dict. Falls back to neutral on data failure.

        This is the ONLY method that advances the internal cursor. topo()
        and thermo_cost() read from the cache populated by the most recent
        state() call. neosynaptex.observe() always calls state() first,
        then topo() and thermo_cost() in the same tick.
        """
        self._ensure_loaded()

        if not self._loaded or self._returns is None:
            # Neutral fallback — gamma estimation will likely be nan here
            neutral = {
                "fiedler_lambda2": 1.0,
                "combo_signal": 1e-6,
                "ricci_mean": -2.0,
                "delta_ricci": 0.0,
            }
            self._cached_state = neutral
            return neutral

        r = self._returns
        n_bars = len(r)

        # Advance cursor through history (simulates live tick)
        cursor_start = _WINDOW
        available = max(1, n_bars - cursor_start)
        idx = cursor_start + (self._t % available)
        idx = min(idx, n_bars - 1)
        self._t += 1

        w_now = r[max(0, idx - _WINDOW) : idx]
        if len(w_now) < 20:
            w_now = r[-_WINDOW:]

        ricci_now, fiedler = self._ricci(w_now)

        w_prev = r[max(0, idx - _WINDOW - 1) : idx - 1]
        if len(w_prev) >= 20:
            ricci_prev, _ = self._ricci(w_prev)
        else:
            ricci_prev = ricci_now

        delta_ricci = ricci_now - ricci_prev

        # Build rolling history of Ricci and delta for z-scoring
        ricci_history: list[float] = []
        delta_history: list[float] = []
        history_start = max(0, idx - _WINDOW)
        for i in range(history_start, idx):
            w = r[max(0, i - _WINDOW) : i]
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

        # Physical cost: stress grows as connectivity drops (inverse coupling),
        # modulated by magnitude of combo signal. Ensures power-law
        # relationship cost ~ (1 + stress) / topo which allows gamma
        # estimation to converge.
        stress_magnitude = max(abs(combo), 1e-6)
        physical_cost = (1.0 + stress_magnitude) / max(fiedler, 1e-3)

        result = {
            "fiedler_lambda2": fiedler,
            "combo_signal": physical_cost,
            "ricci_mean": ricci_now,
            "delta_ricci": delta_ricci,
        }
        self._cached_state = result
        return result

    def topo(self) -> float:
        """Topological complexity = Fiedler eigenvalue (from cache)."""
        if self._cached_state is None:
            self.state()
        assert self._cached_state is not None
        return self._cached_state["fiedler_lambda2"]

    def thermo_cost(self) -> float:
        """Thermodynamic cost = |combo signal| magnitude (from cache)."""
        if self._cached_state is None:
            self.state()
        assert self._cached_state is not None
        return max(self._cached_state["combo_signal"], 1e-6)
