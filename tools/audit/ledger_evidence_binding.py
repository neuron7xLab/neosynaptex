"""Recompute ledger evidence hashes from disk; fail on drift.

Phase 2.1 hardening — closes the B1 (format-only) and B2 (stale-hash)
breakpoints surfaced by the Phase 2 adversarial audit.

Contract
--------

Every entry in ``evidence/gamma_ledger.json`` whose ``data_sha256`` or
``adapter_code_hash`` is non-null MUST also declare a binding under

    "hash_binding": {
        "data_sha256_source":      "<repo-relative path>",
        "adapter_code_hash_source": "<repo-relative path>"
    }

This tool walks every binding, computes the SHA-256 of the named file,
and compares it to the stored value using constant-time comparison
(``hmac.compare_digest``). Drift = hard fail (exit 2). The schema
validator only checks 64-hex format; this tool is the binding layer.

Honest-null contract
--------------------

* ``stored == None  AND  source == None``: ADMITTED (no claim made).
* ``stored != None  AND  source == None``: REJECTED — unbound hash
  ("hash theatre").
* ``stored == None  AND  source != None``: REJECTED — binding without
  a value.
* both non-null: hashes must match.

Exit codes
----------

* 0 — every declared hash matches its on-disk source.
* 2 — at least one entry is unbound, missing, or drifting.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

__all__ = [
    "BindingError",
    "collect_violations",
    "compute_file_hash",
    "main",
]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEDGER = _REPO_ROOT / "evidence" / "gamma_ledger.json"


class BindingError(ValueError):
    """Raised when a ledger entry's stored hash does not match disk."""


def compute_file_hash(path: Path) -> str:
    """Return the SHA-256 hex of ``path`` (streaming, 1 MiB chunks)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_HASH_FIELDS: tuple[tuple[str, str], ...] = (
    ("data_sha256", "data_sha256_source"),
    ("adapter_code_hash", "adapter_code_hash_source"),
)


def collect_violations(ledger: dict, *, repo_root: Path = _REPO_ROOT) -> list[str]:
    """Return human-readable binding violations across the ledger.

    Empty list ↔ every declared hash matches its declared source.
    """
    out: list[str] = []
    for sid, entry in ledger.get("entries", {}).items():
        if not isinstance(entry, dict):
            out.append(f"{sid}: entry is not a dict")
            continue
        binding = entry.get("hash_binding") or {}
        if not isinstance(binding, dict):
            out.append(f"{sid}: hash_binding must be a dict")
            continue
        for hash_field, source_field in _HASH_FIELDS:
            stored = entry.get(hash_field)
            source = binding.get(source_field)
            if stored is None and source is None:
                continue  # honest null
            if stored is None and source is not None:
                out.append(
                    f"{sid}: {hash_field}=null but hash_binding.{source_field}={source!r} "
                    "(declared source without a hash)"
                )
                continue
            if stored is not None and source is None:
                out.append(
                    f"{sid}: {hash_field}={stored[:16]}... declared without "
                    f"hash_binding.{source_field} — UNBOUND HASH"
                )
                continue
            path = repo_root / str(source)
            if not path.is_file():
                out.append(f"{sid}: {hash_field} → {source} (file does not exist on disk)")
                continue
            actual = compute_file_hash(path)
            if not hmac.compare_digest(str(stored), actual):
                out.append(
                    f"{sid}: {hash_field} DRIFT — "
                    f"stored {str(stored)[:16]}... vs actual {actual[:16]}... "
                    f"(source={source})"
                )
    return out


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default=str(_LEDGER), type=Path)
    args = parser.parse_args(argv)
    if not args.ledger.is_file():
        print(f"ERROR: ledger not found: {args.ledger}", file=sys.stderr)
        return 2
    try:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: ledger JSON parse error: {exc}", file=sys.stderr)
        return 2
    violations = collect_violations(ledger)
    if violations:
        print(
            f"BINDING DRIFT: {len(violations)} hash(es) unbound, missing, or drifted:",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 2
    bound = sum(
        1
        for e in ledger.get("entries", {}).values()
        if e.get("data_sha256") or e.get("adapter_code_hash")
    )
    print(
        f"OK: every declared hash recomputed against disk; "
        f"{bound} entr(ies) carry at least one binding."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
