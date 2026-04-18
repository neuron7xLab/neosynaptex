"""Contract ↔ test consistency check for ``core.decision_bridge``.

    python -m tools.audit.decision_bridge_contracts

* Fails if any ``enforced_by`` entry in ``docs/contracts/decision_bridge.yaml``
  does not resolve to a real test (file exists AND symbol grep-matches).
* Fails if every ``I-DB-*`` identifier mentioned in the source tree is
  absent from the YAML (guards against drift in the other direction).

Exit codes:

    0  YAML and tests agree.
    1  YAML references a test that does not exist.
    2  Source mentions an invariant ID not registered in YAML.
    3  YAML is malformed.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_REPO = Path(__file__).resolve().parents[2]
_YAML_PATH = _REPO / "docs" / "contracts" / "decision_bridge.yaml"

_ID_RE = re.compile(r"I-DB(?:-[A-Z])?-\d+")
_ENFORCED_RE = re.compile(r"^(?P<file>tests/[^:]+)::(?P<symbol>[\w:]+)$")

_SOURCE_SCAN_ROOTS = (_REPO / "core", _REPO / "tests")


@dataclass(frozen=True)
class ContractCheckReport:
    ok: bool
    missing_tests: list[tuple[str, str, str]]  # (inv_id, file, symbol)
    unregistered_ids: list[str]
    yaml_error: str | None


def _load_yaml() -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _scan_source_for_ids(roots: tuple[Path, ...]) -> set[str]:
    """All I-DB-* identifiers actually cited in code or tests."""
    found: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in _ID_RE.findall(text):
                found.add(m)
    return found


def _enforced_test_exists(file_rel: str, symbol: str) -> bool:
    file_path = _REPO / file_rel
    if not file_path.exists():
        return False
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Symbols look like "TestClass::test_method" — require both pieces.
    parts = symbol.split("::")
    return all(part in text for part in parts)


def check() -> ContractCheckReport:
    data = _load_yaml()
    if data is None or "invariants" not in data:
        return ContractCheckReport(
            ok=False,
            missing_tests=[],
            unregistered_ids=[],
            yaml_error=f"failed to parse {_YAML_PATH}",
        )

    missing: list[tuple[str, str, str]] = []
    registered_ids: set[str] = set()

    for inv in data["invariants"]:
        inv_id = str(inv.get("id", "?"))
        registered_ids.add(inv_id)
        for entry in inv.get("enforced_by", []):
            m = _ENFORCED_RE.match(str(entry))
            if m is None:
                missing.append((inv_id, entry, "(malformed enforced_by entry)"))
                continue
            rel_file = m.group("file")
            symbol = m.group("symbol")
            if not _enforced_test_exists(rel_file, symbol):
                missing.append((inv_id, rel_file, symbol))

    source_ids = _scan_source_for_ids(_SOURCE_SCAN_ROOTS)
    unregistered = sorted(source_ids - registered_ids)

    return ContractCheckReport(
        ok=not missing and not unregistered,
        missing_tests=missing,
        unregistered_ids=unregistered,
        yaml_error=None,
    )


def main() -> int:
    report = check()
    if report.yaml_error is not None:
        print(f"error: {report.yaml_error}", file=sys.stderr)
        return 3
    if report.missing_tests:
        print("YAML references tests that do not exist:", file=sys.stderr)
        for inv_id, f, s in report.missing_tests:
            print(f"  {inv_id}: {f}::{s}", file=sys.stderr)
        return 1
    if report.unregistered_ids:
        print(
            "Source cites invariant IDs not registered in YAML:",
            file=sys.stderr,
        )
        for i in report.unregistered_ids:
            print(f"  {i}", file=sys.stderr)
        return 2
    print("decision_bridge contracts: YAML and tests agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
