"""Binance public-REST kline fetcher — no API key required.

Binance exposes historical OHLCV ("kline") data via:

    GET /api/v3/klines?symbol=<SYM>&interval=<INT>&startTime=<MS>&limit=<N>

No authentication for this endpoint. Public-data terms permit
research use; redistribution rules apply only to bulk data
mirroring, not to derived γ-fits.

Each kline is a list of 12 fields (Binance v3 spec):

    [openTime, open, high, low, close, volume, closeTime,
     quoteAssetVolume, numberOfTrades, takerBuyBaseAssetVolume,
     takerBuyQuoteAssetVolume, ignore]

We use openTime, close, and numberOfTrades for downstream γ-work.

The fetcher delegates to ``curl`` via subprocess because Python's
``urllib.request`` has shown timeout problems in the sandbox.
``curl`` is a hard dependency — same as for the FRED substrate.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import pathlib
import subprocess
import time

__all__ = [
    "BinanceFetch",
    "fetch_klines",
    "fetch_klines_range",
]

_BASE = "https://api.binance.com/api/v3/klines"


@dataclasses.dataclass(frozen=True)
class BinanceFetch:
    """Provenance record for one Binance kline fetch (possibly paginated)."""

    symbol: str
    interval: str
    start_ms: int
    end_ms: int
    n_klines: int
    sha256: str
    fetched_utc: str
    pages: int

    def as_provenance_dict(self) -> dict:
        return dataclasses.asdict(self)


def _curl_get(url: str, *, timeout_s: float = 30.0) -> bytes:
    """Single GET via curl. Raises on non-zero exit."""

    result = subprocess.run(
        ["curl", "-sf", "--max-time", str(int(timeout_s)), url],
        capture_output=True,
        check=True,
    )
    return result.stdout


def fetch_klines(
    symbol: str,
    interval: str,
    *,
    start_ms: int | None = None,
    end_ms: int | None = None,
    limit: int = 1000,
) -> list[list]:
    """Single-page fetch (max 1000 klines per Binance limit)."""

    parts = [f"symbol={symbol}", f"interval={interval}", f"limit={limit}"]
    if start_ms is not None:
        parts.append(f"startTime={start_ms}")
    if end_ms is not None:
        parts.append(f"endTime={end_ms}")
    url = f"{_BASE}?{'&'.join(parts)}"
    raw = _curl_get(url)
    return json.loads(raw)


def fetch_klines_range(
    symbol: str,
    interval: str,
    *,
    start_ms: int,
    end_ms: int,
    out_path: pathlib.Path | None = None,
    page_pause_s: float = 0.1,
) -> tuple[list[list], BinanceFetch]:
    """Paginated fetch over an arbitrary [start_ms, end_ms) window.

    Returns (klines_list, BinanceFetch provenance record). If
    ``out_path`` is given, also writes the JSON to disk.

    Pagination handles the 1000-kline-per-call Binance limit by
    advancing ``startTime`` to the last returned kline's openTime
    + interval.
    """

    interval_ms = _interval_to_ms(interval)
    all_klines: list[list] = []
    cur = start_ms
    pages = 0
    while cur < end_ms:
        chunk = fetch_klines(symbol, interval, start_ms=cur, end_ms=end_ms, limit=1000)
        if not chunk:
            break
        all_klines.extend(chunk)
        pages += 1
        cur = int(chunk[-1][0]) + interval_ms
        if len(chunk) < 1000:
            break
        if page_pause_s > 0:
            time.sleep(page_pause_s)

    payload = json.dumps(all_klines).encode()
    sha = hashlib.sha256(payload).hexdigest()
    fetched = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if out_path is not None:
        out_path = pathlib.Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(payload)

    return all_klines, BinanceFetch(
        symbol=symbol,
        interval=interval,
        start_ms=start_ms,
        end_ms=end_ms,
        n_klines=len(all_klines),
        sha256=sha,
        fetched_utc=fetched,
        pages=pages,
    )


def _interval_to_ms(interval: str) -> int:
    """Convert Binance interval string to milliseconds."""

    n = int(interval[:-1])
    unit = interval[-1]
    if unit == "m":
        return n * 60_000
    if unit == "h":
        return n * 3_600_000
    if unit == "d":
        return n * 86_400_000
    if unit == "w":
        return n * 604_800_000
    raise ValueError(f"unsupported interval: {interval}")


def klines_to_close_series(klines: list[list]) -> list[float]:
    """Extract the close-price column from a Binance klines payload."""

    return [float(k[4]) for k in klines]
