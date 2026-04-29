"""Tests for tools.audit.ledger_evidence_binding (Phase 2.1).

Numbered tests:
1.  Real repository ledger has every declared hash bound to disk.
2.  Stored hash with no source path → REJECTED (UNBOUND HASH).
3.  Source path with stored=null → REJECTED (declared source without hash).
4.  Stored hash that doesn't match disk → REJECTED (DRIFT).
5.  Source file that does not exist → REJECTED.
6.  ``stored=None AND source=None`` → ADMITTED (honest null).
7.  ``hash_binding`` non-dict → REJECTED.
8.  ``compute_file_hash`` matches stdlib for a known fixture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.audit.ledger_evidence_binding import (
    BindingError,
    collect_violations,
    compute_file_hash,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LEDGER = _REPO_ROOT / "evidence" / "gamma_ledger.json"


# 1
def test_real_ledger_passes_binding() -> None:
    ledger = json.loads(_LEDGER.read_text(encoding="utf-8"))
    violations = collect_violations(ledger)
    assert violations == [], f"binding drift in canonical ledger: {violations}"


# 2
def test_unbound_hash_rejected(tmp_path: Path) -> None:
    fixture = tmp_path / "f.txt"
    fixture.write_bytes(b"x")
    ledger = {
        "entries": {
            "x": {
                "data_sha256": "a" * 64,
                "adapter_code_hash": None,
                # no hash_binding section at all
            }
        }
    }
    v = collect_violations(ledger, repo_root=tmp_path)
    assert any("UNBOUND HASH" in s for s in v)


# 3
def test_source_without_hash_rejected(tmp_path: Path) -> None:
    fixture = tmp_path / "f.txt"
    fixture.write_bytes(b"x")
    ledger = {
        "entries": {
            "x": {
                "data_sha256": None,
                "adapter_code_hash": None,
                "hash_binding": {"data_sha256_source": "f.txt"},
            }
        }
    }
    v = collect_violations(ledger, repo_root=tmp_path)
    assert any("declared source without a hash" in s for s in v)


# 4
def test_drift_detected(tmp_path: Path) -> None:
    fixture = tmp_path / "f.txt"
    fixture.write_bytes(b"x")
    ledger = {
        "entries": {
            "x": {
                "data_sha256": "deadbeef" * 8,
                "adapter_code_hash": None,
                "hash_binding": {"data_sha256_source": "f.txt"},
            }
        }
    }
    v = collect_violations(ledger, repo_root=tmp_path)
    assert any("DRIFT" in s for s in v)


# 5
def test_missing_source_file_rejected(tmp_path: Path) -> None:
    ledger = {
        "entries": {
            "x": {
                "data_sha256": "a" * 64,
                "adapter_code_hash": None,
                "hash_binding": {"data_sha256_source": "does/not/exist.txt"},
            }
        }
    }
    v = collect_violations(ledger, repo_root=tmp_path)
    assert any("does not exist on disk" in s for s in v)


# 6
def test_honest_null_admitted(tmp_path: Path) -> None:
    ledger = {
        "entries": {
            "x": {
                "data_sha256": None,
                "adapter_code_hash": None,
                "hash_binding": {},
            }
        }
    }
    assert collect_violations(ledger, repo_root=tmp_path) == []


# 7
def test_non_dict_hash_binding_rejected(tmp_path: Path) -> None:
    ledger = {
        "entries": {
            "x": {
                "data_sha256": None,
                "adapter_code_hash": None,
                "hash_binding": "not-a-dict",
            }
        }
    }
    v = collect_violations(ledger, repo_root=tmp_path)
    assert any("hash_binding must be a dict" in s for s in v)


# 8
def test_compute_file_hash_matches_stdlib(tmp_path: Path) -> None:
    p = tmp_path / "f.bin"
    payload = b"phase-2.1-binding-test" * 1000
    p.write_bytes(payload)
    assert compute_file_hash(p) == hashlib.sha256(payload).hexdigest()


def test_binding_error_class_exists() -> None:
    # Imported but currently raised only from CLI; assert symbol stable.
    assert issubclass(BindingError, ValueError)
