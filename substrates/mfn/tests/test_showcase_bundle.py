from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_showcase_run_generates_bundle() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "showcase_run.py")],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out_dir = root / "artifacts" / "showcase"
    assert (out_dir / "index.html").exists()
    manifest = json.loads((out_dir / "showcase_manifest.json").read_text(encoding="utf-8"))
    assert manifest["product"] == "Morphology-aware Field Intelligence Engine"
    assert Path(manifest["report_dir"]).exists()
