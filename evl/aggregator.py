"""Cross-session aggregator -- beta trajectory across sessions.

Each session produces one beta. Multiple sessions produce a trajectory.
If beta converges toward 1.0 over sessions -> metastability is a stable attractor.

Author: Yaroslav Vasylenko / neuron7xLab
License: AGPL-3.0-or-later
"""

from __future__ import annotations

import numpy as np
from scipy.stats import theilslopes


def aggregate_sessions(sessions: list[dict]) -> dict:
    """Aggregate beta values across multiple sessions.

    Args:
        sessions: list of dicts with at least "beta" and "session" keys

    Returns:
        dict with beta_mean, beta_std, beta_trajectory, n_sessions,
        convergence info
    """
    betas = [s["beta"] for s in sessions if np.isfinite(s.get("beta", float("nan")))]
    if not betas:
        return {"status": "NO_VALID_SESSIONS", "n_sessions": 0}

    return {
        "status": "OK",
        "n_sessions": len(betas),
        "beta_mean": round(float(np.mean(betas)), 4),
        "beta_std": round(float(np.std(betas)), 4),
        "beta_min": round(float(np.min(betas)), 4),
        "beta_max": round(float(np.max(betas)), 4),
        "beta_trajectory": [round(b, 4) for b in betas],
        "metastable_fraction": round(sum(1 for b in betas if abs(b - 1.0) < 0.15) / len(betas), 3),
        "sessions": [s.get("session", f"s{i}") for i, s in enumerate(sessions)],
    }


def detect_convergence(
    betas: list[float],
    target: float = 1.0,
) -> dict:
    """Detect if beta trajectory converges toward target.

    Uses Theil-Sen slope on |beta - target| over session index.
    Negative slope = converging.

    Args:
        betas:  list of beta values in session order
        target: convergence target (default 1.0)

    Returns:
        dict with slope, converging bool, first/last distance
    """
    betas_arr = np.array(betas, dtype=np.float64)
    valid = np.isfinite(betas_arr)
    betas_arr = betas_arr[valid]

    if len(betas_arr) < 3:
        return {"status": "INSUFFICIENT", "n": len(betas_arr)}

    distances = np.abs(betas_arr - target)
    x = np.arange(len(distances), dtype=np.float64)

    slope, _, _, _ = theilslopes(distances, x)

    return {
        "status": "OK",
        "slope": round(float(slope), 6),
        "converging": slope < 0,
        "first_distance": round(float(distances[0]), 4),
        "last_distance": round(float(distances[-1]), 4),
        "n_sessions": len(betas_arr),
        "target": target,
    }


def load_all_sessions(evidence_dir: str = "evidence/sessions") -> list[dict]:
    """Load analysis.json from all session directories."""
    from pathlib import Path

    sessions = []
    base = Path(evidence_dir)
    for session_dir in sorted(base.glob("session_*")):
        analysis_file = session_dir / "analysis.json"
        if analysis_file.exists():
            import json

            data = json.loads(analysis_file.read_text())
            psd = data.get("psd_latency", {})
            if psd.get("status") == "OK":
                sessions.append(
                    {
                        "session": data.get("session", session_dir.name),
                        "beta": psd["beta"],
                        "accuracy_pct": data.get("statistics", {}).get("accuracy_pct", 0),
                        "n_tasks": data.get("statistics", {}).get("n_tasks", 0),
                    }
                )
    return sessions
