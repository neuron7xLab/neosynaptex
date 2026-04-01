from __future__ import annotations

import json
from pathlib import Path

from bnsyn.cli import main


def test_smoke_command_writes_report(monkeypatch, tmp_path: Path, capsys) -> None:
    out = tmp_path / "smoke.json"
    monkeypatch.setattr(
        "sys.argv",
        ["bnsyn", "smoke", "--seed", "123", "--out", out.as_posix()],
    )

    try:
        main()
    except SystemExit as exc:
        assert exc.code == 0

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["seed"] == 123
    stdout = capsys.readouterr().out
    assert "smoke_report" in stdout
