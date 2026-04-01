from __future__ import annotations

import json
from pathlib import Path

from scripts.intelligence_cycle import ROOT, main, run_cycle_pipeline


EXPECTED_KEYS = {
    "RAW_SIGNAL_SET",
    "FILTERED_CORE",
    "COMPRESSED_SCHEMA",
    "SYSTEM_MODEL",
    "VALIDATED_MODEL",
    "INTELLECTUAL_OBJECT",
}


def test_run_cycle_pipeline_is_deterministic() -> None:
    payload_first = run_cycle_pipeline(ROOT)
    payload_second = run_cycle_pipeline(ROOT)

    assert set(payload_first) == EXPECTED_KEYS
    assert payload_first == payload_second
    assert payload_first["RAW_SIGNAL_SET"]["signals"]
    assert payload_first["FILTERED_CORE"]["essential_elements"]


def test_main_writes_json_output(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "cycle_report.json"
    monkeypatch.setattr("sys.argv", ["intelligence_cycle.py", "--output", str(output_path)])

    exit_code = main()
    assert exit_code == 0
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(payload) == EXPECTED_KEYS
    assert isinstance(payload["VALIDATED_MODEL"]["risk_vectors"], list)
