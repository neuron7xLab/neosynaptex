from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARBITRATION_LOG_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "03_decisions" / "ARBITRATION_LOG.json"


def load_arbitration_log() -> dict[str, object]:
    payload = json.loads(ARBITRATION_LOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "ARBITRATION_LOG.json must be a JSON object"
        raise ValueError(msg)
    return payload


if __name__ == "__main__":
    load_arbitration_log()
