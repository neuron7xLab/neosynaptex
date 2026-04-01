from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_coverage_gate import METRIC_NAME, read_coverage_percent  # noqa: E402


def _git_sha(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True)
        return out.strip()
    except Exception:
        return "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate coverage baseline from coverage.xml")
    parser.add_argument("--coverage-xml", type=Path, default=Path("coverage.xml"))
    parser.add_argument("--output", type=Path, default=Path("quality/coverage_gate.json"))
    parser.add_argument("--minimum-percent", type=float, default=99.0)
    args = parser.parse_args()

    current = read_coverage_percent(args.coverage_xml)
    data = {
        "baseline_percent": round(current, 2),
        "minimum_percent": round(float(args.minimum_percent), 2),
        "metric": METRIC_NAME,
        "generated_from": _git_sha(ROOT),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote baseline to {args.output}")
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
