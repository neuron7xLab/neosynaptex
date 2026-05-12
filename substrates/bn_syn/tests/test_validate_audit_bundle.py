from pathlib import Path

from scripts.validate_audit_bundle import main


def test_validate_audit_bundle_missing_log(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "sample.exit").write_text("0")
    monkeypatch.setattr("sys.argv", ["validate_audit_bundle.py", str(tmp_path)])
    assert main() == 1


def test_validate_audit_bundle_valid_pair(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "release_gate.exit").write_text("0")
    (tmp_path / "release_gate.log").write_text('{"returncode": 0}')
    monkeypatch.setattr("sys.argv", ["validate_audit_bundle.py", str(tmp_path)])
    assert main() == 0
