from __future__ import annotations

from dataclasses import dataclass
import re
from datetime import datetime, timezone


@dataclass(frozen=True)
class LedgerEntry:
    artifact_id: str
    claim_id: str
    status: str
    retention_hash: str
    timestamp_utc: str


class ArtifactLedger:
    """Append-only artifact ledger for auditability."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def append(self, artifact_id: str, claim_id: str, status: str, retention_hash: str) -> LedgerEntry:
        if not re.fullmatch(r"[0-9a-f]{64}", retention_hash or ""):
            raise ValueError("retention_hash must be lowercase SHA-256 hex")
        entry = LedgerEntry(
            artifact_id=artifact_id,
            claim_id=claim_id,
            status=status,
            retention_hash=retention_hash,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[LedgerEntry]:
        return list(self._entries)
