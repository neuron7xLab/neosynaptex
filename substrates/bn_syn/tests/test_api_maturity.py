from __future__ import annotations

from pathlib import Path

from scripts.validate_api_maturity import validate_maturity_file


def test_api_maturity_file_is_valid() -> None:
    errors = validate_maturity_file(Path("docs/api_maturity.json"))
    assert errors == []


def test_api_maturity_rejects_invalid_status(tmp_path: Path) -> None:
    file = tmp_path / "api_maturity.json"
    file.write_text('{"version":1,"modules":{"bnsyn.config":"alpha"}}', encoding="utf-8")
    errors = validate_maturity_file(file)
    assert any("invalid status" in msg for msg in errors)
