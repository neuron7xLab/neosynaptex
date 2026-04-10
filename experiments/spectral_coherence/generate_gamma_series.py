"""Generate two independent γ time series — BN-Syn and GeoSync.

Each adapter is wrapped in its own Neosynaptex instance with zero shared
state. γ is derived per tick from (topo, thermo_cost) via the canonical
gamma estimator inside Neosynaptex.observe(). We never assign or smooth γ
here — it is read verbatim from gamma_per_domain.

Output:
    gamma_bnsyn.npy    — raw γ series from BN-Syn (length = N_TICKS)
    gamma_geosync.npy  — raw γ series from GeoSync (length = N_TICKS)

RULE ZERO:
    γ is DERIVED, never assigned. NaN entries (insufficient data in the
    rolling window) are preserved verbatim so downstream stationarity
    checks can decide whether to drop or difference.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Ensure repo root on sys.path when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from neosynaptex import Neosynaptex  # noqa: E402
from substrates.bn_syn.adapter import BnSynAdapter  # noqa: E402
from substrates.geosync_market.adapter import GeoSyncMarketAdapter  # noqa: E402

N_TICKS = 500
OUT_DIR = Path(__file__).resolve().parent


def _run_single(adapter: object, domain: str, n_ticks: int, label: str) -> np.ndarray:
    """Observe one adapter in isolation and return the raw γ series."""
    nx = Neosynaptex(window=16)
    nx.register(adapter)  # type: ignore[arg-type]
    gamma = np.full(n_ticks, np.nan, dtype=np.float64)
    print(f"Running {label}...")
    for i in range(n_ticks):
        state = nx.observe()
        gamma[i] = state.gamma_per_domain.get(domain, np.nan)
        if i % 50 == 0:
            print(f"  {label}: {i}/{n_ticks}")
    valid = int(np.isfinite(gamma).sum())
    print(f"  {label} complete — valid={valid}/{n_ticks}")
    return gamma


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    gamma_bnsyn = _run_single(BnSynAdapter(), domain="spike", n_ticks=N_TICKS, label="BN-Syn")
    gamma_geosync = _run_single(
        GeoSyncMarketAdapter(lookback_days=120),
        domain="geosync_market",
        n_ticks=N_TICKS,
        label="GeoSync",
    )

    np.save(OUT_DIR / "gamma_bnsyn.npy", gamma_bnsyn)
    np.save(OUT_DIR / "gamma_geosync.npy", gamma_geosync)

    print()
    print(f"Saved to {OUT_DIR}/")
    print(
        f"  BN-Syn  valid: {int(np.isfinite(gamma_bnsyn).sum())}/{N_TICKS}  "
        f"range=[{np.nanmin(gamma_bnsyn):.3f}, {np.nanmax(gamma_bnsyn):.3f}]"
    )
    print(
        f"  GeoSync valid: {int(np.isfinite(gamma_geosync).sum())}/{N_TICKS}  "
        f"range=[{np.nanmin(gamma_geosync):.3f}, {np.nanmax(gamma_geosync):.3f}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
