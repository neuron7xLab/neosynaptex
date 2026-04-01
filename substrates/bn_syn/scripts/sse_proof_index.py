from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/sse_sdo/07_quality/EVIDENCE_INDEX.md")
    args = parser.parse_args()

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    quality = json.loads((ROOT / "artifacts/sse_sdo/07_quality/quality.json").read_text(encoding="utf-8"))

    lines = ["# EVIDENCE_INDEX", ""]
    for gate in quality.get("gates", []):
        lines.append(f"## {gate['id']} {gate['name']}")
        for evidence in gate.get("evidence", []):
            lines.append(f"- {evidence}")
        lines.append("")
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
