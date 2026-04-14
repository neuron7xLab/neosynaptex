#!/usr/bin/env python3
"""End-to-end BTCUSDT γ-replication driver.

Loads the Binance hourly klines committed in
``evidence/replications/binance_btcusdt_1h/btcusdt_1h_year.json``,
computes log-returns, runs the γ-fit + null suite, writes a
structured result. Mirrors ``run_fred_indpro_replication.py`` for
the FRED macro substrate.

Reuses ``substrates.market_fred.gamma_fit`` for fit + nulls (no
substrate-specific γ logic — the math is identical, only the input
preprocessing differs).
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import logging
import pathlib
import sys

import numpy as np

from substrates.market_crypto.binance_client import klines_to_close_series
from substrates.market_fred.gamma_fit import (
    NullComparison,
    fit_gamma_log_log_psd,
    null_comparison,
)

logger = logging.getLogger(__name__)


def _log_returns(closes: list[float]) -> np.ndarray:
    arr = np.array([c for c in closes if c is not None and c > 0], dtype=float)
    return np.diff(np.log(arr))


def main() -> int:
    logging.basicConfig(level="INFO", format="[%(levelname)s] %(message)s")

    klines_path = pathlib.Path("evidence/replications/binance_btcusdt_1h/btcusdt_1h_year.json")
    out_path = pathlib.Path("evidence/replications/binance_btcusdt_1h/result.json")

    if not klines_path.is_file():
        print(f"missing klines at {klines_path}", file=sys.stderr)
        return 2

    raw = klines_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    klines = json.loads(raw)
    closes = klines_to_close_series(klines)
    returns = _log_returns(closes)
    logger.info("klines: %d, valid log-returns: %d", len(klines), len(returns))

    # nperseg ~512 for higher frequency resolution per reviewer note;
    # sample is large enough (8759 returns).

    # We rely on the default nperseg in fit_gamma_log_log_psd which
    # is min(256, len(x)). Override by trimming x or inlining a
    # variant — for this pilot we stay with default nperseg=256.
    # A specparam-upgrade follow-up will set nperseg>=512 explicitly.

    gamma_fit = fit_gamma_log_log_psd(returns, fs=1.0, bootstrap_n=500, seed=42)
    logger.info(
        "γ=%.4f CI=[%.4f,%.4f] r²=%.3f nfreq=%d",
        gamma_fit.gamma,
        gamma_fit.ci_low,
        gamma_fit.ci_high,
        gamma_fit.r2,
        gamma_fit.n_frequencies_fit,
    )

    nulls = []
    for family in ("shuffled", "ar1", "iaaft"):
        logger.info("null family: %s (n=500)", family)
        try:
            cmp = null_comparison(
                real_gamma=gamma_fit.gamma,
                x=returns,
                null_family=family,
                n_surrogates=500,
                seed=42 + hash(family) % 10_000,
                fs=1.0,
            )
            nulls.append(cmp)
            logger.info(
                "  μ=%.4f σ=%.4f z=%.3f separable=%s",
                cmp.mu,
                cmp.sigma,
                cmp.z_score,
                cmp.separable_at_z3,
            )
        except Exception as exc:
            logger.warning("null %s failed: %s", family, exc)
            nulls.append(
                NullComparison(
                    null_family=family,
                    n_surrogates=0,
                    mu=float("nan"),
                    sigma=float("nan"),
                    z_score=float("nan"),
                    null_ci_low=float("nan"),
                    null_ci_high=float("nan"),
                    real_outside_null_ci=False,
                    separable_at_z3=False,
                )
            )

    all_separable = all(n.separable_at_z3 for n in nulls if n.n_surrogates > 0)

    open_time_min = klines[0][0]
    open_time_max = klines[-1][0]
    range_iso = (
        _dt.datetime.fromtimestamp(open_time_min / 1000, _dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        + "..."
        + _dt.datetime.fromtimestamp(open_time_max / 1000, _dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )

    result = {
        "substrate": "market_crypto",
        "asset": "BTCUSDT",
        "exchange": "binance",
        "interval": "1h",
        "claim_status": "measured" if all_separable else "hypothesized",
        "verdict": (
            "separable_from_all_tested_nulls"
            if all_separable
            else "non_separable_from_at_least_one_null"
        ),
        "gamma": dataclasses.asdict(gamma_fit),
        "nulls": [dataclasses.asdict(n) for n in nulls],
        "provenance": {
            "source": "Binance public REST /api/v3/klines",
            "url_template": (
                "https://api.binance.com/api/v3/klines?"
                "symbol=BTCUSDT&interval=1h&startTime=...&limit=1000"
            ),
            "n_klines": len(klines),
            "interval": "1h",
            "open_time_range_utc": range_iso,
            "klines_sha256": sha,
            "klines_bytes": len(raw),
            "fetched_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetch_method": "curl-via-python-subprocess (urllib timed out in sandbox)",
        },
        "method_hierarchy_cite": ("docs/MEASUREMENT_METHOD_HIERARCHY.md §2.3 (bounded secondary)"),
        "null_hierarchy_cite": "docs/NULL_MODEL_HIERARCHY.md §2.1–2.3",
        "interpretation_boundary": (
            "Measures the aperiodic slope of BTCUSDT hourly log-returns "
            "via Welch-PSD + Theil-Sen (bounded-secondary method). "
            "Does NOT license any claim about market criticality, "
            "crypto-equity equivalence, or cross-substrate convergence. "
            "Does NOT replace the primary specparam/IRASA measurement. "
            "Does NOT generalise to genuine tick-level microstructure "
            "(LOBSTER substrate remains BLOCKED_BY_ACQUISITION). "
            "Hourly resolution and crypto-specific market structure "
            "(24/7, no auctions, leverage reflexivity) make this "
            "substrate independent of FRED macro AND distinct from "
            "traditional equity microstructure. Per "
            "docs/CLAIM_BOUNDARY.md §3.1."
        ),
        "claim_boundary_pointer": "docs/CLAIM_BOUNDARY.md",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("wrote %s", out_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
