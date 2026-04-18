"""Append-only telemetry ledger for the Decision Bridge.

Every bridge evaluation is a decision under uncertainty. When that
decision is challenged post-hoc, the question is not "what did the
code do?" — the code is in git — but "on which observation did it
act?". A Merkle-chained append-only ledger answers that question in a
way that cannot be silently rewritten.

Contracts
---------
L-1  Each event carries a SHA-256 hash over
     (prev_hash || canonical_json_payload). The first event uses a
     zero seed as ``prev_hash``.
L-2  The on-disk format is JSON Lines (.jsonl) — one event per line,
     serialised in canonical order (``sort_keys=True``).
L-3  ``verify`` returns a list of defects and the index of the first
     broken link. An empty defect list means the chain is intact.
L-4  ``append`` is atomic per line: either the whole line lands or
     nothing lands. Concurrent writers to the same path are NOT
     supported (single-writer discipline — the bridge instance).
L-5  The ledger is write-only from the bridge's side. The only read
     path is ``iter_events`` / ``verify``; there is no in-place edit
     API by design.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

__all__ = [
    "LedgerVerification",
    "TelemetryEvent",
    "TelemetryLedger",
]

_HASH_SEED: Final[str] = "0" * 64  # 256-bit zero seed for the first event


def _canonical(payload: dict[str, Any]) -> str:
    """Canonical JSON — sorted keys, no extra whitespace, UTF-8-safe."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _chain_hash(prev_hash: str, event_type: str, payload: dict[str, Any]) -> str:
    body = f"{prev_hash}|{event_type}|{_canonical(payload)}".encode()
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class TelemetryEvent:
    """One link in the ledger."""

    index: int
    tick: int
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    self_hash: str

    def to_json_line(self) -> str:
        return _canonical(
            {
                "index": self.index,
                "tick": self.tick,
                "event_type": self.event_type,
                "payload": self.payload,
                "prev_hash": self.prev_hash,
                "self_hash": self.self_hash,
            }
        )

    @staticmethod
    def from_json_line(raw: str) -> TelemetryEvent:
        obj = json.loads(raw)
        return TelemetryEvent(
            index=int(obj["index"]),
            tick=int(obj["tick"]),
            event_type=str(obj["event_type"]),
            payload=dict(obj["payload"]),
            prev_hash=str(obj["prev_hash"]),
            self_hash=str(obj["self_hash"]),
        )


@dataclass(frozen=True)
class LedgerVerification:
    """Verdict from ``TelemetryLedger.verify``."""

    ok: bool
    n_events: int
    first_broken_index: int | None
    defects: list[str] = field(default_factory=list)


class TelemetryLedger:
    """Append-only, Merkle-chained JSONL writer.

    Usage::

        ledger = TelemetryLedger(Path("runs/bridge.jsonl"))
        ledger.append(tick=42, event_type="snapshot", payload={...})

        verdict = TelemetryLedger.verify(Path("runs/bridge.jsonl"))
        assert verdict.ok
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)
        self._index: int = 0
        self._last_hash: str = _HASH_SEED
        self._hydrate()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def index(self) -> int:
        return self._index

    @property
    def last_hash(self) -> str:
        return self._last_hash

    def append(self, *, tick: int, event_type: str, payload: dict[str, Any]) -> TelemetryEvent:
        self_hash = _chain_hash(self._last_hash, event_type, payload)
        event = TelemetryEvent(
            index=self._index,
            tick=int(tick),
            event_type=str(event_type),
            payload=dict(payload),
            prev_hash=self._last_hash,
            self_hash=self_hash,
        )
        # Line-atomic append — a partial write cannot corrupt earlier lines.
        line = event.to_json_line() + "\n"
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
        self._index += 1
        self._last_hash = self_hash
        return event

    @staticmethod
    def iter_events(path: Path) -> Iterator[TelemetryEvent]:
        p = Path(path)
        if not p.exists():
            return
        with p.open("r", encoding="utf-8") as fh:
            for raw in fh:
                stripped = raw.strip()
                if not stripped:
                    continue
                yield TelemetryEvent.from_json_line(stripped)

    @staticmethod
    def verify(path: Path) -> LedgerVerification:
        defects: list[str] = []
        first_bad: int | None = None
        prev_hash = _HASH_SEED
        n = 0

        for expected_index, event in enumerate(TelemetryLedger.iter_events(path)):
            n = expected_index + 1
            if event.index != expected_index:
                defects.append(
                    f"index out-of-order at position {expected_index}: "
                    f"expected {expected_index}, got {event.index}"
                )
                if first_bad is None:
                    first_bad = expected_index
            if event.prev_hash != prev_hash:
                defects.append(
                    f"prev_hash mismatch at index {event.index}: "
                    f"expected {prev_hash[:12]}…, got {event.prev_hash[:12]}…"
                )
                if first_bad is None:
                    first_bad = event.index
            recomputed = _chain_hash(event.prev_hash, event.event_type, event.payload)
            if recomputed != event.self_hash:
                defects.append(
                    f"self_hash mismatch at index {event.index}: "
                    "content differs from what was signed"
                )
                if first_bad is None:
                    first_bad = event.index
            prev_hash = event.self_hash

        return LedgerVerification(
            ok=not defects,
            n_events=n,
            first_broken_index=first_bad,
            defects=defects,
        )

    def _hydrate(self) -> None:
        """Restore ``_index`` and ``_last_hash`` by walking the existing file."""
        n = 0
        last_hash = _HASH_SEED
        for event in TelemetryLedger.iter_events(self._path):
            last_hash = event.self_hash
            n = event.index + 1
        self._index = n
        self._last_hash = last_hash
