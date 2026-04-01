#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--paths", nargs="+", required=True)
    args = ap.parse_args()

    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    rules = [
        (re.compile(rule["pattern"]), rule["replace"])
        for rule in policy.get("rules", [])
        if rule.get("type") == "regex"
    ]

    for raw in args.paths:
        path = Path(raw)
        if path.is_dir():
            files = [entry for entry in path.rglob("*") if entry.is_file()]
        elif path.exists():
            files = [path]
        else:
            files = []

        for file_path in files:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for regex, replacement in rules:
                text = regex.sub(replacement, text)
            file_path.write_text(text, encoding="utf-8")

    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
