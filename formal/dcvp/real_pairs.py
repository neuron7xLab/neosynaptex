"""Real substrate pairs for DCVP v2.1 — spec §VII.

Each real pair builder wraps a DomainAdapter from ``substrates/`` into a
DCVP γ-stream: step the adapter once per tick, collect topo/cost
history, and compute a rolling log-log slope over the most recent W
samples. That slope is the per-tick γ estimate.

Pre-adapter perturbation (spec §II) is applied to the (topo, cost)
window just before the slope is computed. For autonomous simulators
this is the analog of "raw input stream" — it is the input to the γ
estimator, which is the only stage of the pipeline that actually
consumes data.

Three pairs are registered:

* ``lv_kuramoto``        — LotkaVolterra × Kuramoto
  (ecological competition × coupled oscillators)
* ``bnsyn_grayscott``    — BnSyn × GrayScott
  (critical branching × reaction-diffusion morphogenesis)
* ``geosync_kuramoto``   — GeoSyncMarket × Kuramoto
  (Forman-Ricci market curvature × oscillator criticality)

All three are *independent physics* by construction. If DCVP is
working, the verdict should be ARTIFACT or CONDITIONAL, never
CAUSAL_INVARIANT. A positive on ``geosync_kuramoto`` would be the
extraordinary claim — it would mean γ propagation from real market
micro-structure into a Kuramoto oscillator at criticality, a genuine
cross-substrate invariant.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from formal.dcvp.pairs import SubstratePair, register_pair
from formal.dcvp.perturbation import apply_perturbation
from formal.dcvp.protocol import PerturbationSpec

__all__ = [
    "register_real_pairs",
    "gamma_from_topo_cost_window",
]


# ── Rolling γ estimator ────────────────────────────────────────────────


def gamma_from_topo_cost_window(topo: np.ndarray, cost: np.ndarray) -> float:
    """Fast per-window γ via OLS on (log cost, log topo).

    γ is defined such that ``cost ~ topo^(−γ)``. Returns 1.0 when the
    log-range is too small or the window is degenerate — 1.0 is the
    metastable fixed point, so degenerate windows do not spuriously push
    the series toward either criticality extreme.
    """
    t = np.asarray(topo, dtype=np.float64)
    c = np.asarray(cost, dtype=np.float64)
    mask = np.isfinite(t) & np.isfinite(c) & (t > 0) & (c > 0)
    if mask.sum() < 4:
        return 1.0
    lt = np.log(t[mask])
    lc = np.log(c[mask])
    if np.ptp(lt) < 1e-6:
        return 1.0
    # Centered OLS: slope = cov(lt, lc) / var(lt)
    lt_c = lt - lt.mean()
    lc_c = lc - lc.mean()
    slope = float(np.dot(lt_c, lc_c) / (np.dot(lt_c, lt_c) + 1e-12))
    return -slope  # γ = −slope


# ── Builder factory ────────────────────────────────────────────────────


AdapterFactory = Callable[[int], object]


_BuilderFn = Callable[[int, int, PerturbationSpec], np.ndarray]


def _make_builder(factory: AdapterFactory, window: int = 24) -> _BuilderFn:
    """Return a pair-builder that streams γ(t) from an autonomous adapter."""

    def build(seed: int, n_ticks: int, perturbation: PerturbationSpec) -> np.ndarray:
        rng = np.random.default_rng(seed + 7_919)
        adapter = factory(seed)
        topos: list[float] = []
        costs: list[float] = []

        # Warmup: fill the rolling window.
        for _ in range(window):
            adapter.state()  # type: ignore[attr-defined]
            topos.append(float(adapter.topo()))  # type: ignore[attr-defined]
            costs.append(float(adapter.thermo_cost()))  # type: ignore[attr-defined]

        gammas = np.empty(n_ticks, dtype=np.float64)
        for t in range(n_ticks):
            adapter.state()  # type: ignore[attr-defined]
            topos.append(float(adapter.topo()))  # type: ignore[attr-defined]
            costs.append(float(adapter.thermo_cost()))  # type: ignore[attr-defined]
            topo_win = np.array(topos[-window:], dtype=np.float64)
            cost_win = np.array(costs[-window:], dtype=np.float64)
            # Perturb (topo, cost) — analog of pre-adapter stream for
            # autonomous simulators.
            topo_win = apply_perturbation(topo_win, perturbation, rng)
            cost_win = apply_perturbation(cost_win, perturbation, rng)
            # Keep positivity after additive noise so log() is well-defined.
            topo_win = np.maximum(topo_win, 1e-9)
            cost_win = np.maximum(cost_win, 1e-9)
            gammas[t] = gamma_from_topo_cost_window(topo_win, cost_win)
        return gammas

    return build


# ── Factories for individual substrates (lazy import) ─────────────────


def _lv_factory(seed: int) -> object:
    from substrates.lotka_volterra.adapter import LotkaVolterraAdapter

    return LotkaVolterraAdapter(seed=seed)


def _kuramoto_factory(seed: int) -> object:
    from substrates.kuramoto.adapter import KuramotoAdapter

    return KuramotoAdapter(seed=seed)


def _bnsyn_factory(seed: int) -> object:
    from substrates.bn_syn.adapter import BnSynAdapter

    return BnSynAdapter(seed=seed)


def _grayscott_factory(seed: int) -> object:
    from substrates.gray_scott.adapter import GrayScottAdapter

    return GrayScottAdapter(seed=seed)


def _geosync_factory(seed: int) -> object:
    from substrates.geosync_market.adapter import GeoSyncMarketAdapter

    # Seed does not change the downloaded market data (that is fixed by
    # yfinance at the moment of the run) but is used to break RNG ties in
    # the perturbation layer. We vary lookback_days slightly per seed so
    # different seeds exercise different slices of the market history.
    lookback = 90 + (seed % 5) * 10  # 90..130 days
    return GeoSyncMarketAdapter(lookback_days=lookback)


def register_real_pairs() -> None:
    """Register all real substrate pairs with the DCVP pair registry."""
    register_pair(
        SubstratePair(
            name="lv_kuramoto",
            a_builder=_make_builder(_lv_factory),
            b_builder=_make_builder(_kuramoto_factory),
        )
    )
    register_pair(
        SubstratePair(
            name="bnsyn_grayscott",
            a_builder=_make_builder(_bnsyn_factory),
            b_builder=_make_builder(_grayscott_factory),
        )
    )
    register_pair(
        SubstratePair(
            name="geosync_kuramoto",
            a_builder=_make_builder(_geosync_factory),
            b_builder=_make_builder(_kuramoto_factory),
        )
    )
