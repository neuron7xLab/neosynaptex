#!/usr/bin/env python3
"""Generate SHA-256 manifest for reproducibility freeze bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    out = (root / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    include_roots = ["scripts", "docs", "manuscript", "evidence", "core", "neosynaptex.py"]
    files: list[Path] = []
    for entry in include_roots:
        p = root / entry
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(
                f
                for f in p.rglob("*")
                if f.is_file() and ".git" not in f.parts and "__pycache__" not in f.parts
            )

    records = []
    for f in sorted(files):
        rel = f.relative_to(root).as_posix()
        records.append({"path": rel, "sha256": _sha256_file(f), "bytes": f.stat().st_size})

    manifest_sha = out / "MANIFEST.sha256"
    with manifest_sha.open("w", encoding="utf-8") as mf:
        for rec in records:
            mf.write(f"{rec['sha256']}  {rec['path']}\n")

    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    }
    (out / "manifest.json").write_text(
        json.dumps({"entries": records, "environment": env}, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(records)} entries to {out}")


if __name__ == "__main__":
    main()
