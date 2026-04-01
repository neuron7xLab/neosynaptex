from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import scan_governed_docs  # noqa: E402


def test_scan_governed_docs_main_success(tmp_path: Path, monkeypatch: object) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    inventory = docs_dir / "INVENTORY.md"
    governed_doc = docs_dir / "governed.md"

    inventory.write_text(
        "Intro\n\n```yaml\ngoverned_docs:\n  - docs/governed.md\n```\n",
        encoding="utf-8",
    )
    governed_doc.write_text(
        "Requirement [NORMATIVE][CLM-0001] must remain stable.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(scan_governed_docs, "ROOT", tmp_path)
    monkeypatch.setattr(scan_governed_docs, "INVENTORY", inventory)

    assert scan_governed_docs.main() == 0
