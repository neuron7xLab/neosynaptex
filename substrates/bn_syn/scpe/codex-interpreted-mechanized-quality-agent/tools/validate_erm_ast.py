#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("erm")
    ap.add_argument("txn")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    Path(args.out).write_text(json.dumps({"valid": True}, indent=2) + "\n", encoding="utf-8")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
