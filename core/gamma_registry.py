"""Gamma Registry -- single programmatic API for all gamma values.

All gamma values MUST come from gamma_ledger.json via this registry.
INV-1: gamma derived only, never assigned.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

_LEDGER_PATH = Path(__file__).resolve().parent.parent / "evidence" / "gamma_ledger.json"


class GammaRegistryError(Exception):
    pass


class GammaRegistry:
    """Read-only gateway to gamma_ledger.json with hash verification."""

    _cache: Optional[Dict[str, Any]] = None
    _ledger_hash: Optional[str] = None

    @classmethod
    def _load(cls, force: bool = False) -> Dict[str, Any]:
        if cls._cache is not None and not force:
            return cls._cache
        if not _LEDGER_PATH.exists():
            raise GammaRegistryError(f"Ledger not found: {_LEDGER_PATH}")
        raw = _LEDGER_PATH.read_bytes()
        cls._ledger_hash = hashlib.sha256(raw).hexdigest()
        cls._cache = json.loads(raw)
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
            raise GammaRegistryError(
                f"Field '{field}' not in entry '{entry_id}'"
            )
        return entry[field]

    @classmethod
    def get_entry(cls, entry_id: str) -> Dict[str, Any]:
        ledger = cls._load()
        entries = ledger.get("entries", {})
        if entry_id not in entries:
            raise GammaRegistryError(f"Unknown entry: {entry_id}")
        return dict(entries[entry_id])

    @classmethod
    def is_locked(cls, entry_id: str) -> bool:
        return bool(cls.get(entry_id, "locked"))

    @classmethod
    def all_entries(cls) -> Dict[str, Dict[str, Any]]:
        ledger = cls._load()
        return dict(ledger.get("entries", {}))

    @classmethod
    def verify_hash(cls, entry_id: str, expected_hash: str) -> bool:
        entry = cls.get_entry(entry_id)
        ds = entry.get("data_source", {})
        actual = ds.get("sha256")
        if actual is None:
            return False
        return actual == expected_hash

    @classmethod
    def locked_entries(cls) -> Dict[str, Dict[str, Any]]:
        return {
            k: v for k, v in cls.all_entries().items()
            if v.get("locked", False)
        }

    @classmethod
    def requires_rederivation(cls) -> Dict[str, Dict[str, Any]]:
        return {
            k: v for k, v in cls.all_entries().items()
            if v.get("status") == "REQUIRES_REDERIVATION"
        }

    @classmethod
    def invalidate_cache(cls) -> None:
        cls._cache = None
        cls._ledger_hash = None
