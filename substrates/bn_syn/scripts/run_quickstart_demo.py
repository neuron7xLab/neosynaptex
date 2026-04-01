#!/usr/bin/env python3
"""Generate and validate the canonical quickstart demo artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

DEMO_TIMEOUT_SECONDS = 30
CANONICAL_DEMO_CMD: tuple[str, ...] = (
    sys.executable,
    "-m",
    "bnsyn",
    "demo",
    "--steps",
    "120",
    "--dt-ms",
    "0.1",
    "--seed",
    "123",
    "--N",
    "32",
)
ARTIFACT_PATH = Path("artifacts/demo.json")


def _validate_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RuntimeError("demo output must be a JSON object")
    demo = payload.get("demo")
    if not isinstance(demo, dict) or not demo:
        raise RuntimeError("demo output must contain a non-empty 'demo' object")
    return payload


def _tail_40_lines(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-40:])


def main() -> int:
    try:
        ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"cannot create artifacts directory: {exc}") from exc

    try:
        proc = subprocess.run(
            CANONICAL_DEMO_CMD,
            check=True,
            capture_output=True,
            text=True,
            timeout=DEMO_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"timeout {DEMO_TIMEOUT_SECONDS}s: {' '.join(CANONICAL_DEMO_CMD)}"
        ) from exc
    except subprocess.CalledProcessError as exc:
        combined = (exc.stdout or "") + "\n" + (exc.stderr or "")
        raise RuntimeError(
            f"command failed rc={exc.returncode}: {' '.join(CANONICAL_DEMO_CMD)} | {_tail_40_lines(combined).strip()}"
        ) from exc

    try:
        payload = _validate_payload(json.loads(proc.stdout))
    except json.JSONDecodeError as exc:
        raise RuntimeError("demo command did not return valid JSON") from exc

    try:
        with ARTIFACT_PATH.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        raise RuntimeError(f"cannot write artifacts/demo.json: {exc}") from exc

    print("Demo artifact written: artifacts/demo.json")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"quickstart demo FAILED: {exc}")
        raise SystemExit(1)
