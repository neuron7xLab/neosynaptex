from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def test_verify_reproducible_artifacts_passes(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    script = tmp_path / "gen.py"
    script.write_text(
        f"from pathlib import Path\nPath({artifact.as_posix()!r}).write_text('stable\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    spec = tmp_path / "spec.json"
    report = tmp_path / "report.json"
    spec.write_text(
        json.dumps([{"artifact": str(artifact), "command": f"python {script}"}]), encoding="utf-8"
    )

    proc = _run(
        [
            "python",
            "-m",
            "scripts.verify_reproducible_artifacts",
            "--spec",
            str(spec),
            "--runs",
            "3",
            "--report",
            str(report),
        ]
    )
    assert proc.returncode == 0, proc.stderr
    assert "PASS reproducibility" in proc.stdout
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload[0]["status"] == "pass"


def test_verify_reproducible_artifacts_fails_on_drift(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.txt"
    script = tmp_path / "gen.py"
    script.write_text(
        f"from pathlib import Path\nimport uuid\nPath({artifact.as_posix()!r}).write_text(str(uuid.uuid4()), encoding='utf-8')\n",
        encoding="utf-8",
    )
    spec = tmp_path / "spec.json"
    report = tmp_path / "report.json"
    spec.write_text(
        json.dumps([{"artifact": str(artifact), "command": f"python {script}"}]), encoding="utf-8"
    )

    proc = _run(
        [
            "python",
            "-m",
            "scripts.verify_reproducible_artifacts",
            "--spec",
            str(spec),
            "--runs",
            "3",
            "--report",
            str(report),
        ]
    )
    assert proc.returncode == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload[0]["status"] == "non_deterministic"
