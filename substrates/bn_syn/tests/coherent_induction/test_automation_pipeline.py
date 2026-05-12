from __future__ import annotations

import json
from pathlib import Path

from scripts.automate_coherent_induction_v2 import main


def test_automation_pipeline_generates_artifacts() -> None:
    rc = main()
    assert rc == 0
    root = Path(__file__).resolve().parents[2]
    report = root / "docs" / "reports" / "ten_x_start_quality_report.md"
    ledger = root / "examples" / "ledger_entry_v2.json"
    assert report.exists()
    assert ledger.exists()
    payload = json.loads(ledger.read_text())
    assert payload["final_verdict"] in {"PASS", "FAIL"}
