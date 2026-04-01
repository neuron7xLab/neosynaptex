#!/usr/bin/env python3
"""Verify CI artifact manifest semantics, checksums, and producer provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

VALID_ARTIFACT_CLASSES = {"required", "optional", "diagnostic"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_rel_path(raw_path: str, prefixes: Iterable[str]) -> str | None:
    normalized = raw_path.replace("\\", "/").lstrip("./")
    for prefix in prefixes:
        pfx = prefix.replace("\\", "/").lstrip("./")
        if not pfx:
            continue
        if not pfx.endswith("/"):
            pfx = pfx + "/"
        if normalized.startswith(pfx):
            normalized = normalized[len(pfx):]
            break
    normalized = normalized.lstrip("./")
    if not normalized or normalized.startswith("/") or ".." in Path(normalized).parts:
        return None
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--root", default=".")
    parser.add_argument("--expected-producer", required=True)
    parser.add_argument("--name-prefix", required=True)
    parser.add_argument("--strip-path-prefix", action="append", default=[])
    parser.add_argument("--require-name", action="append", default=[])
    args = parser.parse_args()

    root = Path(args.root).resolve()
    mpath = Path(args.manifest_json).resolve()
    doc = json.loads(mpath.read_text(encoding="utf-8"))

    if not isinstance(doc, dict) or not isinstance(doc.get("artifacts"), list):
        print("ARTIFACT_MANIFEST_INVALID_SHAPE")
        return 2

    failures: list[str] = []
    seen_required_names: set[str] = set()
    for i, item in enumerate(doc["artifacts"]):
        if not isinstance(item, dict):
            failures.append(f"bad-item-{i}")
            continue
        name = item.get("name")
        rel = item.get("path")
        sz = item.get("size_bytes")
        digest = item.get("sha256")
        producer = item.get("producer_job")
        artifact_class = item.get("artifact_class", "required")

        if artifact_class not in VALID_ARTIFACT_CLASSES:
            failures.append(f"artifact-class-invalid:{name}:{artifact_class}")
        if producer != args.expected_producer:
            failures.append(f"producer-mismatch:{name}:{producer}")
        if not isinstance(name, str) or not name.startswith(args.name_prefix):
            failures.append(f"name-noncanonical:{name}")
        if not isinstance(rel, str):
            failures.append(f"path-missing:{name}")
            continue
        normalized_rel = normalize_rel_path(rel, args.strip_path_prefix)
        if normalized_rel is None:
            failures.append(f"path-invalid:{rel}")
            continue
        p = (root / normalized_rel).resolve()
        if root not in p.parents and p != root:
            failures.append(f"path-escape:{rel}")
            continue
        if not p.exists():
            failures.append(f"missing-file:{normalized_rel}")
            continue
        actual_size = p.stat().st_size
        min_allowed_size = 0 if artifact_class == "diagnostic" else 1
        if not isinstance(sz, int) or sz < min_allowed_size or sz != actual_size:
            failures.append(f"size-mismatch:{normalized_rel}:{sz}:{actual_size}")
        actual_sha = sha256_file(p)
        if digest != actual_sha:
            failures.append(f"sha-mismatch:{normalized_rel}")

        if artifact_class == "required" and isinstance(name, str):
            seen_required_names.add(name)

    for required_name in args.require_name:
        if required_name not in seen_required_names:
            failures.append(f"required-artifact-missing:{required_name}")

    if failures:
        print("\n".join(failures))
        return 2

    print("CI_ARTIFACT_MANIFEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
