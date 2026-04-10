"""Append-only γ-channel with rolling SHA256 checksum.

Spec §I — Communication: append-only γ-channel + checksum, no feedback.
The channel is a write-once NDJSON file; each line is

    {"t": int, "gamma": float, "checksum": str}

where `checksum` = sha256(prev_checksum || payload). Any retroactive edit
to a line breaks the chain and is detected by `verify`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "GammaChannel",
    "GammaSample",
    "ChannelTampered",
]

_GENESIS = "0" * 64


class ChannelTampered(RuntimeError):
    """Raised when the rolling checksum chain fails verification."""


@dataclass(frozen=True)
class GammaSample:
    t: int
    gamma: float
    checksum: str


def _link(prev: str, t: int, gamma: float) -> str:
    payload = f"{prev}|{t}|{gamma:.17g}".encode()
    return hashlib.sha256(payload).hexdigest()


class GammaChannel:
    """Append-only γ-channel backed by an NDJSON file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._last_checksum = _GENESIS
        self._n = 0
        if self._path.exists():
            # Re-open existing channel — recompute last checksum.
            for sample in self._replay():
                self._last_checksum = sample.checksum
                self._n += 1

    @property
    def path(self) -> Path:
        return self._path

    @property
    def length(self) -> int:
        return self._n

    def append(self, t: int, gamma: float) -> GammaSample:
        checksum = _link(self._last_checksum, t, gamma)
        record = {"t": int(t), "gamma": float(gamma), "checksum": checksum}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        self._last_checksum = checksum
        self._n += 1
        return GammaSample(t=t, gamma=float(gamma), checksum=checksum)

    def _replay(self) -> Iterator[GammaSample]:
        prev = _GENESIS
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                expected = _link(prev, int(rec["t"]), float(rec["gamma"]))
                if expected != rec["checksum"]:
                    raise ChannelTampered(
                        f"chain broken at t={rec['t']}: expected {expected[:12]}…, "
                        f"got {str(rec['checksum'])[:12]}…"
                    )
                prev = str(rec["checksum"])
                yield GammaSample(t=int(rec["t"]), gamma=float(rec["gamma"]), checksum=prev)

    def read(self) -> list[GammaSample]:
        return list(self._replay())

    def verify(self) -> bool:
        try:
            list(self._replay())
        except ChannelTampered:
            return False
        return True
