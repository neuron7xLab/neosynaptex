"""Export openapi."""

from __future__ import annotations

import json
from pathlib import Path

from mycelium_fractal_net.integration.api_server import app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "evidence" / "wave_4"
BASELINE = ROOT / "docs" / "contracts"
OUT.mkdir(parents=True, exist_ok=True)
BASELINE.mkdir(parents=True, exist_ok=True)


def main() -> int:
    schema = app.openapi()
    schema.setdefault("info", {})["version"] = "openapi-v2"
    text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    (OUT / "openapi.json").write_text(text, encoding="utf-8")
    (OUT / "openapi.v2.json").write_text(text, encoding="utf-8")
    if not (BASELINE / "openapi.v2.json").exists():
        (BASELINE / "openapi.v2.json").write_text(text, encoding="utf-8")
    if not (BASELINE / "openapi.v1.json").exists():
        (BASELINE / "openapi.v1.json").write_text(text, encoding="utf-8")
    print(OUT / "openapi.v2.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
