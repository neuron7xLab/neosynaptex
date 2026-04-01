from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path


def main() -> int:
    artifact = Path("artifacts/demo.json")
    manifest = Path("artifacts/reproduce_manifest.json")
    sha_file = Path("artifacts/demo.sha256")

    if not artifact.exists():
        raise SystemExit("missing required artifact: artifacts/demo.json")

    sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    sha_file.write_text(f"{sha}  {artifact}\n", encoding="utf-8")

    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        git_sha = "UNKNOWN"

    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "artifact": str(artifact),
                "sha256": sha,
                "python": platform.python_version(),
                "git_sha": git_sha,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"WROTE {manifest}")
    print(f"WROTE {sha_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
