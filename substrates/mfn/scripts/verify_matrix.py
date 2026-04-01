"""Verify matrix."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "evidence" / "wave_1"
OUT.mkdir(parents=True, exist_ok=True)
GROUPS = [
    [
        "tests/test_engine_v1_surface.py",
        "tests/test_public_api_structure.py",
        "tests/test_layer_boundaries.py",
    ],
    [
        "tests/test_schema_roundtrip_completion.py",
        "tests/test_artifact_pipeline_completion.py",
        "tests/test_api_server_completion.py",
    ],
    [
        "tests/test_scenario_pipelines_completion.py",
        "tests/test_integration_api_cli.py",
        "tests/test_determinism.py",
    ],
]


def main() -> int:
    summary = []
    overall_ok = True
    for idx, group in enumerate(GROUPS, start=1):
        cmd = [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", *group]
        started = time.time()
        log_path = OUT / f"pytest_group_{idx}.log"
        with log_path.open("w", encoding="utf-8") as fh:
            fh.write(f"$ {' '.join(cmd)}\n\n")
            proc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, text=True)
        elapsed = time.time() - started
        summary.append(
            {
                "group": idx,
                "targets": group,
                "returncode": proc.returncode,
                "elapsed_seconds": round(elapsed, 3),
                "log": str(log_path.relative_to(ROOT)),
            }
        )
        overall_ok &= proc.returncode == 0
    payload = {"ok": overall_ok, "groups": summary}
    (OUT / "pytest.log").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
