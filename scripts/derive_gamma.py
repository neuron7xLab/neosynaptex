#!/usr/bin/env python3
"""Derive gamma values from mock adapters and update gamma_ledger.json.

This script runs each mock adapter for sufficient ticks to accumulate
topo/cost pairs, then computes gamma via Theil-Sen regression with
bootstrap CI — the same _per_domain_gamma function used at runtime.

For real substrates (zebrafish, gray_scott, kuramoto, bnsyn) that have
no raw data in this repository, entries are marked PENDING_DATA.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from neosynaptex import _per_domain_gamma

LEDGER_PATH = Path(__file__).resolve().parent.parent / "evidence" / "gamma_ledger.json"
N_TICKS = 100


def derive_mock(adapter, entry_id: str, expected_gamma: float) -> dict:
    """Run adapter for N_TICKS, collect topo/cost, derive gamma."""
    topos = []
    costs = []
    for _ in range(N_TICKS):
        adapter.state()  # advance tick
        t = adapter.topo()
        c = adapter.thermo_cost()
        topos.append(t)
        costs.append(c)

    topo_arr = np.array(topos)
    cost_arr = np.array(costs)
    g, r2, ci_lo, ci_hi, _boot = _per_domain_gamma(topo_arr, cost_arr, seed=42)

    print(f"  {entry_id}: gamma={g:.4f}, r2={r2:.4f}, CI=[{ci_lo:.4f}, {ci_hi:.4f}]")
    print(f"    expected={expected_gamma}, error={abs(g - expected_gamma):.4f}")
    print(f"    n_pairs={len(topo_arr)}")

    return {
        "gamma": round(float(g), 6),
        "ci_low": round(float(ci_lo), 6),
        "ci_high": round(float(ci_hi), 6),
        "r2": round(float(r2), 6),
        "n_pairs": int(len(topo_arr)),
        "p_permutation": None,
        "status": "DERIVED",
        "locked": True,
    }


def main():
    ledger = json.loads(LEDGER_PATH.read_text())

    # Mock adapter derivation removed — ledger contains only VALIDATED entries.
    # Mock adapters remain in neosynaptex.py for testing but are not
    # registered in the evidence ledger.

    # Mark real substrates as PENDING_DATA (no raw data in this repo)
    for entry_id in ["zebrafish_wt", "gray_scott", "kuramoto", "bnsyn"]:
        entry = ledger["entries"][entry_id]
        entry["status"] = "PENDING_DATA"
        print(f"\n  {entry_id}: marked PENDING_DATA (no raw data in repo)")

    LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + "\n")
    print(f"\nLedger updated: {LEDGER_PATH}")


if __name__ == "__main__":
    main()
