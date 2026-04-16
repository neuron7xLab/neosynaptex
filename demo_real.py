#!/usr/bin/env python3
"""neosynaptex demo -- admissible substrates only.

Previously this script advertised "ALL REAL substrates. Zero mocks" and
registered ``CnsAiLoopAdapter`` alongside genuine recorded substrates,
even though the CNS-AI claim was downgraded to ``falsified_downgraded``
on 2026-04-14 (see ``docs/CLAIM_BOUNDARY_CNS_AI.md``). That was a
provenance breach: a downgraded synthetic fixture does not belong in a
pipeline labelled "real".

The CNS-AI adapter has been removed from this demo. The remaining
substrates each derive their own admissibility -- ``demo_real.py``
does not itself guarantee REAL-mode registration, but it MUST NOT
register an adapter whose ``claim_status`` is ``downgraded`` or
``forbidden``. Enforcement lives in
``contracts.provenance.ensure_admissible`` and is covered by
``tests/audit/test_cns_ai_provenance_boundary.py``.
"""

import numpy as np

from neosynaptex import Neosynaptex
from substrates.bn_syn.adapter import BnSynAdapter
from substrates.gray_scott.adapter import GrayScottAdapter
from substrates.kuramoto.adapter import KuramotoAdapter
from substrates.zebrafish.adapter import ZebrafishAdapter


def _f(v: float, w: int = 6) -> str:
    return f"{v:.3f}".rjust(w) if np.isfinite(v) else "n/a".rjust(w)


def main() -> None:
    nx = Neosynaptex(window=16, mode="demo")

    # Substrates WITHOUT downgraded provenance. CNS-AI is deliberately
    # excluded here; see module docstring.
    nx.register(ZebrafishAdapter("WT"))
    nx.register(GrayScottAdapter())
    nx.register(KuramotoAdapter())
    nx.register(BnSynAdapter())

    for _ in range(50):
        s = nx.observe()
        print(
            f"  t={s.t:02d}  "
            f"gamma={_f(s.gamma_mean)}  "
            f"dg/dt={_f(s.dgamma_dt)}  "
            f"sr={_f(s.spectral_radius)}  "
            f"coh={_f(s.cross_coherence)}  "
            f"p={_f(s.universal_scaling_p)}  "
            f"phase={s.phase}"
        )

    print()
    print("=" * 72)
    print("  NEOSYNAPTEX -- ADMISSIBLE SUBSTRATES")
    print("=" * 72)
    print(f"  gamma_mean       = {_f(s.gamma_mean)}")
    print(f"  gamma_std        = {_f(s.gamma_std)}")
    print(f"  dgamma/dt        = {_f(s.dgamma_dt)}")
    print(f"  cross_coherence  = {_f(s.cross_coherence)}")
    print(f"  universal_p      = {_f(s.universal_scaling_p)}")
    print(f"  spectral_radius  = {_f(s.spectral_radius)}")
    print(f"  phase            = {s.phase}")
    print(f"  resilience       = {_f(s.resilience_score)}")
    print()

    for d in sorted(s.gamma_per_domain):
        g = s.gamma_per_domain[d]
        ci = s.gamma_ci_per_domain[d]
        sr = s.sr_per_domain.get(d, float("nan"))
        anom = s.anomaly_score.get(d, float("nan"))
        mod = s.modulation.get(d, 0.0)
        ci_str = f"[{_f(ci[0], 5)}, {_f(ci[1], 5)}]" if np.isfinite(ci[0]) else "[n/a]"
        print(
            f"  {d:12s}  "
            f"g={_f(g, 6)}  "
            f"CI={ci_str}  "
            f"sr={_f(sr, 6)}  "
            f"anom={_f(anom, 5)}  "
            f"mod={mod:+.4f}"
        )

    print()
    proof = nx.export_proof()
    print(f"  Verdict: {proof.get('verdict')}")
    print("=" * 72)


if __name__ == "__main__":
    main()
