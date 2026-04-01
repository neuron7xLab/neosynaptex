"""Minimal deterministic library integration example."""

from __future__ import annotations

import json

from bnsyn.sim.network import run_simulation


def main() -> int:
    metrics = run_simulation(steps=120, dt_ms=0.1, seed=123, N=32)
    payload = {
        "example": "library_minimal",
        "seed": 123,
        "metrics": metrics,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
