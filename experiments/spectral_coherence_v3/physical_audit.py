"""Phase 1 — physical audit of BN-Syn and GeoSync intrinsic timescales.

Estimates characteristic timescales directly from simulator dynamics —
NOT from γ. γ is derived downstream; at this stage we probe the raw
internals so that any later spectral peak can be compared against a
physics-motivated prediction.

BN-Syn — uses the pre-computed population firing-rate array
         (_pop_rates from BnSynAdapter). Timescale is estimated from:
           * autocorrelation 1/e decay time
           * dominant PSD peak of the pop_rate signal
           * inter-burst interval (rate > mean + 1σ)
         Unit conversion: 1 experiment tick = 20 internal sim steps
         because BnSynAdapter.state() advances _t by 20 each call.

GeoSync — uses the raw log-return matrix (_returns from
          GeoSyncMarketAdapter, populated after _load()). Timescale is
          estimated from:
            * autocorrelation decay of |aggregate returns|
            * dominant PSD peak of the aggregated |Δr| signal
            * event interval: days where |Δr_mean| > 1σ, gap distribution
          Unit: 1 experiment tick = 1 trading day.

Output: audit.json with timescales in EXPERIMENT ticks (not internal
steps) so they are directly comparable to the γ spectral pipeline.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.signal import welch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from substrates.bn_syn.adapter import BnSynAdapter  # noqa: E402
from substrates.geosync_market.adapter import GeoSyncMarketAdapter  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
PHYSICAL_MATCH_TOLERANCE = 0.05  # spec §I-C

# BnSynAdapter.state() increments internal cursor by 20 per tick.
BNSYN_STEPS_PER_TICK = 20


@dataclass(frozen=True)
class TimescaleReport:
    characteristic_timescale_ticks: float
    estimation_method: str
    supporting_stats: dict[str, Any]


def _acf_decay_time(x: np.ndarray, max_lag: int = 200) -> float:
    """Return lag where normalized ACF first crosses 1/e (~0.368).

    Returns 1.0 if the signal decorrelates within a single step.
    """
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    var = float(np.dot(x, x))
    if var < 1e-12:
        return 1.0
    max_lag = min(max_lag, len(x) // 2)
    target = 1.0 / np.e
    for lag in range(1, max_lag):
        acf = float(np.dot(x[:-lag], x[lag:]) / var)
        if acf < target:
            return float(lag)
    return float(max_lag)


def _dominant_psd_period(x: np.ndarray, fs: float = 1.0) -> tuple[float, float]:
    """Return (period, peak_frequency) of the dominant PSD peak (excluding DC)."""
    nper = min(256, len(x))
    freqs, psd = welch(x - x.mean(), fs=fs, nperseg=nper)
    if len(freqs) < 3:
        return float("nan"), float("nan")
    # Ignore DC.
    psd[0] = 0.0
    idx = int(np.argmax(psd))
    f_peak = float(freqs[idx])
    period = 1.0 / f_peak if f_peak > 1e-9 else float("inf")
    return period, f_peak


def _event_interval(x: np.ndarray, threshold_sigma: float = 1.0) -> float:
    """Mean gap between threshold-crossings of |x − mean| > threshold_sigma · std."""
    x = np.asarray(x, dtype=np.float64)
    x_abs = np.abs(x - x.mean())
    sigma = float(x_abs.std())
    if sigma < 1e-12:
        return float("inf")
    events = np.where(x_abs > threshold_sigma * sigma)[0]
    if events.size < 3:
        return float("inf")
    gaps = np.diff(events)
    return float(gaps.mean())


def _select_primary(psd_ticks: float, acf_ticks: float) -> tuple[float, str]:
    """Pick the most physically meaningful timescale.

    Priority: PSD dominant period when it lies within a Nyquist-valid
    range (≥ 2 ticks and ≤ 1/2 of a typical run length ≈ 200), else ACF
    1/e decay, else infinity. Sub-Nyquist estimates (period < 2 ticks)
    are not directly comparable to the γ spectral pipeline and are
    therefore rejected as primary candidates.
    """
    if np.isfinite(psd_ticks) and 2.0 <= psd_ticks <= 200.0:
        return psd_ticks, "psd"
    if np.isfinite(acf_ticks) and acf_ticks >= 1.0:
        return acf_ticks, "acf"
    return float("inf"), "unavailable"


def audit_bnsyn(seed: int = 42) -> TimescaleReport:
    """Probe BN-Syn intrinsic timescale from its pre-computed pop_rate array."""
    adapter = BnSynAdapter(seed=seed)
    pop_rates = np.asarray(adapter._pop_rates, dtype=np.float64)  # noqa: SLF001

    acf_lag_internal = _acf_decay_time(pop_rates, max_lag=500)
    psd_period_internal, f_peak_internal = _dominant_psd_period(pop_rates)
    burst_interval_internal = _event_interval(pop_rates, threshold_sigma=1.0)

    # Convert internal sim steps → experiment ticks (1 tick = 20 steps).
    acf_ticks = acf_lag_internal / BNSYN_STEPS_PER_TICK
    psd_ticks = psd_period_internal / BNSYN_STEPS_PER_TICK
    burst_ticks = burst_interval_internal / BNSYN_STEPS_PER_TICK

    primary, method = _select_primary(psd_ticks, acf_ticks)

    return TimescaleReport(
        characteristic_timescale_ticks=float(primary),
        estimation_method=method,
        supporting_stats={
            "acf_1e_lag_ticks": float(acf_ticks),
            "psd_dominant_period_ticks": float(psd_ticks),
            "psd_peak_frequency_internal": float(f_peak_internal),
            "burst_interval_ticks": float(burst_ticks),
            "pop_rates_len": int(pop_rates.size),
            "pop_rate_mean": float(pop_rates.mean()),
            "pop_rate_std": float(pop_rates.std()),
            "steps_per_tick": BNSYN_STEPS_PER_TICK,
        },
    )


def audit_geosync(lookback_days: int = 120) -> TimescaleReport:
    """Probe GeoSync intrinsic timescale from its raw log-return matrix."""
    adapter = GeoSyncMarketAdapter(lookback_days=lookback_days)
    adapter.state()  # triggers _load()
    returns = adapter._returns  # noqa: SLF001
    if returns is None:
        return TimescaleReport(
            characteristic_timescale_ticks=float("nan"),
            estimation_method="unavailable",
            supporting_stats={"error": adapter._error},  # noqa: SLF001
        )
    # Aggregate absolute log-return across assets, per day.
    agg = np.mean(np.abs(returns), axis=1)
    acf_lag = _acf_decay_time(agg, max_lag=min(200, len(agg) // 2))
    psd_period, f_peak = _dominant_psd_period(agg)
    event_int = _event_interval(agg, threshold_sigma=1.0)

    # GeoSync is already in experiment-tick units (1 tick = 1 trading day).
    primary, method = _select_primary(psd_period, acf_lag)

    return TimescaleReport(
        characteristic_timescale_ticks=float(primary),
        estimation_method=method,
        supporting_stats={
            "acf_1e_lag_ticks": float(acf_lag),
            "psd_dominant_period_ticks": float(psd_period),
            "psd_peak_frequency": float(f_peak),
            "event_interval_ticks": float(event_int),
            "n_bars": int(returns.shape[0]),
            "n_tickers": int(returns.shape[1]),
            "aggregate_mean": float(agg.mean()),
            "aggregate_std": float(agg.std()),
        },
    )


def run_audit(out_json: Path | None = None) -> dict[str, Any]:
    out_json = out_json or (OUT_DIR / "audit.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)

    bnsyn = audit_bnsyn()
    geosync = audit_geosync()

    t_b = bnsyn.characteristic_timescale_ticks
    t_g = geosync.characteristic_timescale_ticks
    f_b = 1.0 / t_b if np.isfinite(t_b) and t_b > 0 else float("nan")
    f_g = 1.0 / t_g if np.isfinite(t_g) and t_g > 0 else float("nan")
    match = bool(
        np.isfinite(f_b) and np.isfinite(f_g) and abs(f_b - f_g) <= PHYSICAL_MATCH_TOLERANCE
    )

    payload = {
        "bnsyn": asdict(bnsyn),
        "geosync": asdict(geosync),
        "f_bnsyn": float(f_b),
        "f_geosync": float(f_g),
        "physical_frequency_match": match,
        "physical_match_tolerance": PHYSICAL_MATCH_TOLERANCE,
    }
    out_json.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    report = run_audit()
    print(json.dumps(report, indent=2))
