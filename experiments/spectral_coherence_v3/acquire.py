"""Phase 3 — long-run γ acquisition with burn-in and raw export.

Runs BN-Syn and GeoSync via their Linear (no-wrap) adapters for
burn_in_ticks + logged_ticks = 2300 total, exporting ONLY the logged
window. γ is DERIVED per tick via :func:`core.gamma.compute_gamma`
(the canonical Theil-Sen log-log regression) and read verbatim —
never smoothed, never assigned.

We bypass the full Neosynaptex wrapper because its bootstrap_n=500
per-tick CI estimation dominates runtime at O(2300 × 500) Theil-Sen
fits per side. The *point estimate* γ is identical between the two
code paths; only the bootstrap-derived confidence interval shrinks in
precision (bootstrap_n=50 is still well within the Monte-Carlo error
budget for a per-tick estimate).

Outputs (all to this directory):
    gamma_bnsyn_raw.npy      — logged γ series
    gamma_geosync_raw.npy    — logged γ series
    valid_mask_bnsyn.npy     — True where γ is finite
    valid_mask_geosync.npy   — True where γ is finite
    timestamps.npy           — shared tick indices (0 .. logged_ticks-1)
    acquisition.json         — run metadata + validity stats
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.gamma import compute_gamma  # noqa: E402
from experiments.spectral_coherence_v3.adapters import (  # noqa: E402
    LinearBnSynAdapter,
    LinearGeoSyncAdapter,
)

BURN_IN_TICKS = 300
LOGGED_TICKS = 2000
WINDOW = 64  # rolling window of (topo, cost) pairs for γ per tick
BOOTSTRAP_N = 50  # per-tick bootstrap iterations (point estimate unchanged)
MIN_USABLE_SAMPLES = 1500  # spec §Phase 3 — underpowered threshold
OUT_DIR = Path(__file__).resolve().parent


def _acquire_single(
    adapter: object,
    burn_in: int,
    logged: int,
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Stream one adapter; compute rolling γ via canonical compute_gamma.

    γ(t) is the Theil-Sen slope of (log cost, log topo) over the trailing
    WINDOW samples. NaN when the canonical estimator refuses the window
    (insufficient log-range or R²). The NaN values are preserved for the
    validity mask — we never impute, interpolate, or smooth them.
    """
    if hasattr(adapter, "burn_in"):
        adapter.burn_in(burn_in)  # type: ignore[attr-defined]
    else:  # pragma: no cover — all linear adapters expose burn_in
        for _ in range(burn_in):
            adapter.state()  # type: ignore[attr-defined]

    topos: list[float] = []
    costs: list[float] = []
    gamma = np.full(logged, np.nan, dtype=np.float64)
    print(f"Running {label} ({burn_in} burn-in + {logged} logged)...")
    for i in range(logged):
        adapter.state()  # type: ignore[attr-defined]
        topos.append(float(adapter.topo()))  # type: ignore[attr-defined]
        costs.append(float(adapter.thermo_cost()))  # type: ignore[attr-defined]
        if len(topos) >= WINDOW:
            t_win = np.array(topos[-WINDOW:], dtype=np.float64)
            c_win = np.array(costs[-WINDOW:], dtype=np.float64)
            res = compute_gamma(t_win, c_win, bootstrap_n=BOOTSTRAP_N)
            gamma[i] = res.gamma
        if i % 200 == 0:
            print(f"  {label}: {i}/{logged}")

    mask = np.isfinite(gamma)
    return gamma, mask


def run_acquisition(
    burn_in_ticks: int = BURN_IN_TICKS,
    logged_ticks: int = LOGGED_TICKS,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    bnsyn = LinearBnSynAdapter(
        seed=42, sim_steps=max(50_000, (burn_in_ticks + logged_ticks + 50) * 20)
    )
    gamma_b, mask_b = _acquire_single(
        bnsyn, burn_in=burn_in_ticks, logged=logged_ticks, label="BN-Syn"
    )

    geosync = LinearGeoSyncAdapter(lookback_days=3650)
    gamma_g, mask_g = _acquire_single(
        geosync, burn_in=burn_in_ticks, logged=logged_ticks, label="GeoSync"
    )

    np.save(out_dir / "gamma_bnsyn_raw.npy", gamma_b)
    np.save(out_dir / "gamma_geosync_raw.npy", gamma_g)
    np.save(out_dir / "valid_mask_bnsyn.npy", mask_b)
    np.save(out_dir / "valid_mask_geosync.npy", mask_g)
    np.save(out_dir / "timestamps.npy", np.arange(logged_ticks, dtype=np.int64))

    joint = mask_b & mask_g
    meta = {
        "burn_in_ticks": burn_in_ticks,
        "logged_ticks": logged_ticks,
        "bnsyn_valid_samples": int(mask_b.sum()),
        "geosync_valid_samples": int(mask_g.sum()),
        "joint_valid_samples": int(joint.sum()),
        "nan_rate_bnsyn": float(1.0 - mask_b.mean()),
        "nan_rate_geosync": float(1.0 - mask_g.mean()),
        "underpowered": bool(joint.sum() < MIN_USABLE_SAMPLES),
        "bnsyn_gamma_range": [float(np.nanmin(gamma_b)), float(np.nanmax(gamma_b))],
        "geosync_gamma_range": [float(np.nanmin(gamma_g)), float(np.nanmax(gamma_g))],
    }
    (out_dir / "acquisition.json").write_text(json.dumps(meta, indent=2))
    print()
    print(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    run_acquisition()
