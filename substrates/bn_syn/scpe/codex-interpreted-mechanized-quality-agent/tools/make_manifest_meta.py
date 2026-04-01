#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"meta": True, "evidence_root": args.evidence_root}, indent=2) + "\n",
        encoding="utf-8",
    )
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
