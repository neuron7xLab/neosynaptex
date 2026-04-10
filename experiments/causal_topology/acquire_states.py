"""Phase 1 — state-history acquisition for causal topology.

Reuses the linear (no-wrap) adapters from spectral_coherence_v3 so
cycling is physically impossible, then streams per-tick (topo, cost,
state) triples. γ is DERIVED via the canonical :func:`core.gamma.
compute_gamma` on a rolling window; the state dictionaries are
retained so Phase 2 can build a Granger causal graph per tick.

Outputs:
    state_bnsyn.npz   — per-variable state arrays
    state_geosync.npz — per-variable state arrays
    gamma_bnsyn.npy   — derived γ per logged tick
    gamma_geosync.npy — derived γ per logged tick
    valid_mask.npy    — joint valid tick mask
    acquisition.json  — run metadata
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
WINDOW = 64
BOOTSTRAP_N = 50
MIN_USABLE_SAMPLES = 1500
OUT_DIR = Path(__file__).resolve().parent / "results"


def _acquire(
    adapter: object, burn_in: int, logged: int, label: str
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    if hasattr(adapter, "burn_in"):
        adapter.burn_in(burn_in)  # type: ignore[attr-defined]
    else:
        for _ in range(burn_in):
            adapter.state()  # type: ignore[attr-defined]

    topos: list[float] = []
    costs: list[float] = []
    states: list[dict[str, float]] = []
    gamma = np.full(logged, np.nan, dtype=np.float64)
    print(f"Running {label} ({burn_in} burn-in + {logged} logged)...")

    for i in range(logged):
        state = adapter.state()  # type: ignore[attr-defined]
        states.append({k: float(v) for k, v in state.items()})
        topos.append(float(adapter.topo()))  # type: ignore[attr-defined]
        costs.append(float(adapter.thermo_cost()))  # type: ignore[attr-defined]
        if len(topos) >= WINDOW:
            t_win = np.array(topos[-WINDOW:], dtype=np.float64)
            c_win = np.array(costs[-WINDOW:], dtype=np.float64)
            res = compute_gamma(t_win, c_win, bootstrap_n=BOOTSTRAP_N)
            gamma[i] = res.gamma
        if i % 200 == 0:
            print(f"  {label}: {i}/{logged}")

    keys = sorted(states[0].keys()) if states else []
    state_arrays = {k: np.array([s[k] for s in states], dtype=np.float64) for k in keys}
    return gamma, state_arrays


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
    gamma_b, state_b = _acquire(bnsyn, burn_in_ticks, logged_ticks, "BN-Syn")

    geosync = LinearGeoSyncAdapter(lookback_days=3650)
    gamma_g, state_g = _acquire(geosync, burn_in_ticks, logged_ticks, "GeoSync")

    mask_b = np.isfinite(gamma_b)
    mask_g = np.isfinite(gamma_g)
    joint = mask_b & mask_g

    np.save(out_dir / "gamma_bnsyn.npy", gamma_b)
    np.save(out_dir / "gamma_geosync.npy", gamma_g)
    np.save(out_dir / "valid_mask.npy", joint)
    np.savez(out_dir / "state_bnsyn.npz", **state_b)
    np.savez(out_dir / "state_geosync.npz", **state_g)

    meta = {
        "burn_in_ticks": burn_in_ticks,
        "logged_ticks": logged_ticks,
        "bnsyn_valid_samples": int(mask_b.sum()),
        "geosync_valid_samples": int(mask_g.sum()),
        "joint_valid_samples": int(joint.sum()),
        "nan_rate_bnsyn": float(1.0 - mask_b.mean()),
        "nan_rate_geosync": float(1.0 - mask_g.mean()),
        "underpowered": bool(joint.sum() < MIN_USABLE_SAMPLES),
        "bnsyn_state_vars": sorted(state_b.keys()),
        "geosync_state_vars": sorted(state_g.keys()),
    }
    (out_dir / "acquisition.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return meta


if __name__ == "__main__":
    run_acquisition()
