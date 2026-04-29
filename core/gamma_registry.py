"""Gamma Registry -- single programmatic API for all gamma values.

All gamma values MUST come from gamma_ledger.json via this registry.
INV-1: gamma derived only, never assigned.

Phase 2.1 hardening (closes audit-B4 "runtime never validates"): every
load now passes through ``evidence.ledger_schema.validate_ledger``;
schema violations raise :class:`GammaRegistryError` and the cache is
*never* populated. Honest CI failure beats silent runtime drift.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from evidence.ledger_schema import validate_ledger

__all__ = [
    "GammaRegistry",
    "GammaRegistryError",
]

_LEDGER_PATH = Path(__file__).resolve().parent.parent / "evidence" / "gamma_ledger.json"

# Escape hatch for downstream tooling that constructs synthetic ledgers
# in tests. CI sets ``NFI_STRICT_LEDGER=1`` — in production this is the
# default. Tests that need a permissive loader set the env var to ``0``.
_STRICT = os.environ.get("NFI_STRICT_LEDGER", "1") != "0"


class GammaRegistryError(Exception):
    pass


class GammaRegistry:
    """Read-only gateway to gamma_ledger.json with hash verification."""

    _cache: dict[str, Any] | None = None
    _ledger_hash: str | None = None

    @classmethod
    def _load(cls, force: bool = False) -> dict[str, Any]:
        if cls._cache is not None and not force:
            return cls._cache
        if not _LEDGER_PATH.exists():
            raise GammaRegistryError(f"Ledger not found: {_LEDGER_PATH}")
        raw = _LEDGER_PATH.read_bytes()
        ledger_hash = hashlib.sha256(raw).hexdigest()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GammaRegistryError(f"ledger JSON parse error: {exc}") from exc
        if _STRICT:
            errs = validate_ledger(parsed)
            if errs:
                raise GammaRegistryError(
                    f"ledger fails schema validation; runtime refuses to load. violations={errs}"
                )
        # Only mutate cache after validation. Failure leaves cache empty.
        cls._ledger_hash = ledger_hash
        cls._cache = parsed
        return cls._cache

    @classmethod
    def ledger_hash(cls) -> str:
        cls._load()
        return cls._ledger_hash  # type: ignore[return-value]

    @classmethod
    def get(cls, entry_id: str, field: str = "gamma") -> Any:
        ledger = cls._load()
        entries = ledger.get("entries", {})
        if entry_id not in entries:
            raise GammaRegistryError(f"Unknown entry: {entry_id}")
        entry = entries[entry_id]
        if field not in entry:
            raise GammaRegistryError(f"Field '{field}' not in entry '{entry_id}'")
        return entry[field]

    @classmethod
    def get_entry(cls, entry_id: str) -> dict[str, Any]:
        ledger = cls._load()
        entries = ledger.get("entries", {})
        if entry_id not in entries:
            raise GammaRegistryError(f"Unknown entry: {entry_id}")
        return dict(entries[entry_id])

    @classmethod
    def is_locked(cls, entry_id: str) -> bool:
        return bool(cls.get(entry_id, "locked"))

    @classmethod
    def all_entries(cls) -> dict[str, dict[str, Any]]:
        ledger = cls._load()
        return dict(ledger.get("entries", {}))

    @classmethod
    def verify_hash(cls, entry_id: str, expected_hash: str) -> bool:
        entry = cls.get_entry(entry_id)
        ds = entry.get("data_source", {})
        actual = ds.get("sha256")
        if actual is None:
            return False
        return bool(actual == expected_hash)

    @classmethod
    def locked_entries(cls) -> dict[str, dict[str, Any]]:
        return {k: v for k, v in cls.all_entries().items() if v.get("locked", False)}

    @classmethod
    def requires_rederivation(cls) -> dict[str, dict[str, Any]]:
        return {
            k: v for k, v in cls.all_entries().items() if v.get("status") == "REQUIRES_REDERIVATION"
        }

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
        cls._ledger_hash = None
