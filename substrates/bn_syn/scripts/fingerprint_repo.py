from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_fingerprint(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".git/"):
            continue
        data = path.read_bytes()
        files.append({"path": rel, "size": len(data), "sha256": sha256_bytes(data)})
    return {
        "root": root.name,
        "file_count": len(files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministically fingerprint repository files")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_fingerprint(ROOT)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
