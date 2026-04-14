"""Crypto market substrate — γ-measurement on free public exchange data.

Substrate class: ``market_microstructure_crypto``. Independent of
the FRED macro lane (`substrates/market_fred/`) and independent of
LOBSTER (paid). Provides a SECOND, free-data market substrate so
the cross-substrate convergence framing in
``docs/CLAIM_BOUNDARY.md §3.2`` does not rest on a single market
data source.

Data sources are public exchange REST APIs (Binance, Coinbase) —
no API keys, no contracts, no DUAs. Higher-frequency than monthly
FRED macro (1-hour vs 1-month), so produces a substantively
different statistical regime.

Caveats (per ``docs/CLAIM_BOUNDARY.md §3.1`` scope qualifiers):

* "Microstructure" here is at hourly resolution. Genuine
  tick-level microstructure (LOBSTER nanosecond) remains
  ``BLOCKED_BY_ACQUISITION``.
* Crypto-USD pairs have known structural differences from
  traditional equity microstructure (24/7 trading, no opening
  auction, fragmented liquidity across exchanges, leverage
  reflexivity). γ-claims on this substrate DO NOT generalise to
  equity microstructure without explicit replication.
* Single asset (BTCUSDT) on single exchange (Binance) per pilot.
  Multi-exchange consistency is a follow-up control, not in
  scope of the initial run.
"""
