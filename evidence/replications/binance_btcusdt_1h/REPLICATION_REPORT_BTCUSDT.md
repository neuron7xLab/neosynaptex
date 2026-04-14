# BTCUSDT Hourly γ-Replication Report — v1.0

> **Substrate.** `market_crypto / btcusdt_1h`. Distinct from
> `market_macro` (FRED INDPRO, monthly). Distinct from
> `market_microstructure_lobster` (NASDAQ tick-level, BLOCKED).
> **Protocol.** γ-program Phase VI (independent of §Step 23 FRED).
> **Method.** Bounded secondary — Welch-PSD + Theil-Sen.
> **Pair.** `docs/CLAIM_BOUNDARY.md`,
> `docs/MEASUREMENT_METHOD_HIERARCHY.md §2.3`,
> `docs/NULL_MODEL_HIERARCHY.md §2.1–2.3`.
> **Date.** 2026-04-14.

## 1. TL;DR — substrate-level falsification at this resolution

- **γ = 0.0045** on BTCUSDT hourly log-returns, 8759 returns over
  1 year (Apr 2025 – Apr 2026 UTC, Binance).
- CI95 = [-0.0271, +0.0393]; **r² = 0.001**.
- **Spectrum is statistically flat** at hourly resolution — i.e.,
  the data is consistent with white-noise log-returns. No
  1/f^γ scaling regime is detectable.
- Three null families tested (shuffled, AR(1), IAAFT) all yield
  |z| < 0.2 — γ_real is **statistically indistinguishable** from
  every null.

**Verdict for cross-substrate γ ≈ 1 framing.** This substrate
provides **negative evidence** at this resolution: hourly
BTCUSDT log-returns do not exhibit a fittable critical-regime
γ-marker. Per `CLAIM_BOUNDARY.md §3.2`, this NARROWS the
admissible cross-substrate convergence claim — it cannot be
universal across all market substrates and all resolutions; at
minimum the hourly crypto-USD pair is excluded.

**This is not a method failure.** This is an honest, expected
finding: mature crypto-USD markets are approximately efficient
at hourly resolution (martingale-ish), and an efficient-market
log-return spectrum IS approximately flat by construction.

## 2. Provenance

| Field | Value |
|---|---|
| Source | Binance public REST API |
| Endpoint | `GET /api/v3/klines` |
| Symbol | `BTCUSDT` |
| Interval | `1h` |
| Time range | 2025-04-14 → 2026-04-14 (1 year UTC) |
| n klines | 8760 |
| n valid log-returns | 8759 |
| Auth | None (public endpoint) |
| Fetch method | `curl` via Python `subprocess` |
| sha256 of payload | see `result.json :: provenance.klines_sha256` |
| Bytes | ~1.7 MB JSON |

The raw klines payload is committed at
`evidence/replications/binance_btcusdt_1h/btcusdt_1h_year.json`
so the full replication is self-contained.

## 3. Method

| Component | Choice | Rationale |
|---|---|---|
| Signal | log-returns of close prices | Standard efficient-market test |
| Sampling fs | 1.0 (cycles/hour) | Native hourly frequency |
| PSD | Welch, `nperseg = 256`, detrend=constant | scipy.signal.welch |
| Exponent fit | Theil-Sen on log(f)-log(PSD) | Robust per §MEASUREMENT_METHOD_HIERARCHY.md §2.3 |
| Bootstrap | 500 resamples | conservative CI |

**Reviewer note acknowledged.** Per the FRED report reviewer:
specparam upgrade requires nperseg ≥ 512 for adequate frequency
resolution. This pilot uses default 256 (128 freq bins for
8759 returns). With γ ≈ 0 the question of whether nperseg=512
would change the verdict is meaningful only if there is a
non-zero slope to estimate; the current measurement does not
show one. The specparam-upgrade follow-up will explicitly use
nperseg ≥ 512.

## 4. Result — point estimate

| Quantity | Value |
|---|---|
| γ | 0.0045 |
| CI95 low | -0.0271 |
| CI95 high | +0.0393 |
| r² | 0.001 |
| n frequencies fit | 128 |
| n samples (log-returns) | 8759 |

**γ ≈ 0 with r² ≈ 0** is the signature of a white-noise spectrum.
The Welch-PSD is essentially flat in log-log; no slope to
extract. CI95 brackets zero with width ~0.07 — narrow given the
8759-sample size.

## 5. Null comparison

| Null family | Required? | μ_surrogate | σ_surrogate | z-score | separable? |
|---|---|---|---|---|---|
| shuffled | yes | 0.0008 | 0.0191 | 0.191 | NO |
| IAAFT | yes | 0.0036 | 0.0058 | 0.149 | NO |
| AR(1) | yes (OU substitute) | 0.0062 | 0.0197 | -0.088 | NO |
| Poisson | N/A (continuous) | — | — | — | — |
| latent-variable | DEFERRED — §NULL_MODEL_HIERARCHY.md §2.5 | — | — | — | — |

**All three tested nulls reproduce γ ≈ 0** because the underlying
data is white-noise-like. This is the trivial outcome when there
is no scaling structure to test against.

The right reading: this is NOT a "null reproduces γ thus criticality
falsified" outcome of the kind `NULL_MODEL_HIERARCHY.md §6` warns
against. It is a "no fittable γ exists in the first place" outcome.
The substrate at this resolution / method choice does not admit
a γ-claim, full stop.

## 6. What this result LICENSES

- **Substrate-class narrowing.** The cross-substrate convergence
  framing in `CLAIM_BOUNDARY.md §3.2` cannot be inflated to
  cover hourly crypto-USD as supportive evidence. Whether or not
  any future positive substrate result lands, BTCUSDT hourly
  must be cited as an explicit non-supportive substrate.
- **Two-substrate market-lane evidence.** Combined with the
  FRED INDPRO pilot (#98), the market lane now has TWO
  independent substrates with different failure modes:
  - FRED macro: γ ≈ 0.94, AR(1)-non-separable (γ explained by
    linear autocorrelation).
  - BTCUSDT hourly: γ ≈ 0, white-noise spectrum (no scaling).
  Both fail to support a market-critical γ ≈ 1 claim — for
  different reasons.

## 7. What this result does NOT license

- **Does NOT** falsify the possibility of crypto microstructure
  criticality at sub-second / tick-level resolution. Hourly is
  too coarse to capture micro-burst dynamics.
- **Does NOT** falsify γ ≈ 1 in the neural / morphogenetic lanes;
  this is one substrate, one resolution, one method.
- **Does NOT** replace the specparam-primary measurement upgrade
  (in this case the upgrade would not change the qualitative
  outcome but would tighten the CI).
- **Does NOT** generalise to traditional equity microstructure
  (different market structure, different counterparty mix,
  different opening-auction effects). LOBSTER acquisition
  remains the gating step for that substrate.
- **Does NOT** contradict any specific economics literature on
  crypto efficiency — efficient-market evidence at hourly
  resolution is mainstream (see Urquhart 2016; Bariviera 2017;
  Tran & Leirvik 2020 on BTC market efficiency).

## 8. Cross-substrate market-lane state after this run

| Substrate row in `SUBSTRATE_MEASUREMENT_TABLE.yaml` | Method | γ | Verdict |
|---|---|---|---|
| `fred_indpro` (macro, monthly, 1919–2026) | Welch + Theil-Sen | 0.94 | hypothesized; AR(1)-non-separable |
| `btcusdt_1h` (microstructure-ish, hourly, 1yr) | Welch + Theil-Sen | 0.00 | hypothesized; white-noise spectrum, all nulls indistinguishable |
| `lobster_lob` (true microstructure, ns) | — | — | BLOCKED_BY_ACQUISITION |

Two free-data market substrates. Two honest negative findings
(in different ways). No support for cross-substrate γ ≈ 1 from
the market lane on the bounded-secondary method tested.

## 9. Replication instructions

To reproduce from a fresh checkout:

```bash
# Fetch (curl, paginated 1000-kline calls)
mkdir -p evidence/replications/binance_btcusdt_1h
END_MS=$(date +%s000)
START_MS=$((END_MS - 365*24*3600*1000))
python3 -c "
import urllib.request, json, subprocess, time
hour_ms = 3600 * 1000
all_klines = []
cur = $START_MS
end = $END_MS
while cur < end:
    url = f'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={cur}&endTime={end}&limit=1000'
    chunk = json.loads(subprocess.check_output(['curl','-sf','--max-time','30',url]))
    if not chunk: break
    all_klines.extend(chunk)
    cur = chunk[-1][0] + hour_ms
    if len(chunk) < 1000: break
import pathlib
pathlib.Path('evidence/replications/binance_btcusdt_1h/btcusdt_1h_year.json').write_text(json.dumps(all_klines))
"

# Fit + null comparison
python run_btcusdt_replication.py
```

Determinism: seed = 42. Same window + same Binance bytes → identical
result to within floating-point tolerance. Note Binance kline data
for already-closed candles is immutable (unlike LOBSTER); historical
runs reproduce exactly.

## 10. Next steps

1. **Specparam/IRASA upgrade with nperseg ≥ 512.** Confirms qualitative
   verdict (white-noise) under primary method.
2. **Minute-level run.** Same asset, 1-min interval. ~525,600
   samples, may show structure not visible at 1h. Each run is
   its own prereg per `PREREG_TEMPLATE_GAMMA.md`.
3. **Multi-asset crypto control.** ETHUSDT, SOLUSDT, etc. Test
   whether the white-noise verdict is BTC-specific or universal
   across mature crypto-USD pairs.
4. **Multi-exchange consistency.** Same asset on Coinbase + Kraken.
   Substrate-independence within the crypto class.
5. **Avalanche analysis on order-flow events** (Bouchaud 2024 frame).
   Requires either tick-level data (LOBSTER) or order-book stream
   (Binance WebSocket).

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-04-14 | Initial BTCUSDT hourly γ-replication. γ ≈ 0, white-noise spectrum. Substrate stays `hypothesized` (neither supports nor falsifies cross-substrate γ ≈ 1 at this resolution). |

---

**claim_status:** measured (about this report; the γ-claim it contains is `hypothesized` per CLAIM_BOUNDARY.md §6)
**result_json:** `evidence/replications/binance_btcusdt_1h/result.json`
**raw_klines:** `evidence/replications/binance_btcusdt_1h/btcusdt_1h_year.json`
**substrate_table_entry:** to be added — `btcusdt_1h` row in `docs/SUBSTRATE_MEASUREMENT_TABLE.yaml`
