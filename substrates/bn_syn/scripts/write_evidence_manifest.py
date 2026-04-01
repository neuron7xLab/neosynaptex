from __future__ import annotations

import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path
import subprocess
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def run(cmd: list[str]) -> str:
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def main() -> int:
    today = datetime.now(UTC).strftime("%Y%m%d")
    root = Path("artifacts") / "evidence" / today / "local"
    reports = root / "REPORTS"
    reports.mkdir(parents=True, exist_ok=True)

    env_path = root / "ENV.txt"
    env_path.write_text(
        "\n".join(
            [
                f"timestamp={datetime.now(UTC).isoformat()}",
                f"python={run([sys.executable, '--version'])}",
                f"pip={run([sys.executable, '-m', 'pip', '--version'])}",
                f"git_sha={run(['git', 'rev-parse', 'HEAD'])}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    tracked = []
    for candidate in [
        Path("artifacts/flake-report.json"),
        Path("artifacts/flake-report.md"),
        Path("artifacts/tests/junit-all.xml"),
        Path("artifacts/tests/failure-diagnostics.json"),
        Path("artifacts/tests/failure-diagnostics.md"),
    ]:
        if candidate.exists():
            target = reports / candidate.name
            target.write_bytes(candidate.read_bytes())
            tracked.append({"path": str(target), "sha256": sha256(target)})

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": run(["git", "rev-parse", "HEAD"]),
        "artifacts": tracked,
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
