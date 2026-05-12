from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from bnsyn.regime import RegimeController, append_run_record_jsonl, build_run_record


def test_ledger_record_utc_and_jsonl(tmp_path: Path) -> None:
    c = RegimeController(learning_rate=0.01)
    w = np.ones(4)
    g = np.ones(4)
    a = np.ones(128)
    w2, d = c.step(w, g, a, entropy=0.2)
    rec = build_run_record(w, w2, d, {"lr": 0.01, "clip": 1.0}, git_commit_sha="deadbeef")
    assert rec.utc_timestamp.endswith("Z")
    out = tmp_path / "ledger.jsonl"
    append_run_record_jsonl(str(out), rec)
    row = json.loads(out.read_text().strip())
    assert row["status"] == "ok"
    assert row["git_commit_sha"] == "deadbeef"
