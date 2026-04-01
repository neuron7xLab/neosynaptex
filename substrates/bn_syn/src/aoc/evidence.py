from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


def hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def hash_json(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class EvidenceWriter:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir

    def write_json(self, name: str, payload: dict[str, Any]) -> None:
        (self.run_dir / name).write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")

    def write_markdown(self, name: str, content: str) -> None:
        (self.run_dir / name).write_text(content, encoding="utf-8")

    def copy_bundle(self, files: list[str]) -> None:
        bundle = self.run_dir / "evidence_bundle"
        bundle.mkdir(exist_ok=True)
        for f in files:
            src = self.run_dir / f
            if src.exists():
                shutil.copy2(src, bundle / f)
