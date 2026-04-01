"""Run a command and capture deterministic execution logs for PRR evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, help="Primary log path")
    parser.add_argument(
        "--also-log",
        action="append",
        default=[],
        help="Additional log paths to write identical transcript to",
    )
    parser.add_argument("--cwd", default=".")
    parser.add_argument(
        "--env-name",
        action="append",
        default=[],
        help="Environment variable names relevant to this command",
    )
    parser.add_argument("command", help="Exact shell command to execute")
    args = parser.parse_args()

    start = utc_now()
    proc = subprocess.run(
        args.command,
        shell=True,
        cwd=args.cwd,
        text=True,
        capture_output=True,
        env=os.environ.copy(),
        check=False,
    )
    end = utc_now()

    payload = {
        "timestamp_start_utc": start,
        "timestamp_end_utc": end,
        "cwd": str(Path(args.cwd).resolve()),
        "command": args.command,
        "exit_code": proc.returncode,
        "env_delta_names": sorted(set(args.env_name)),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }

    destinations = [Path(args.log), *[Path(item) for item in args.also_log]]
    for path in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=os.sys.stderr)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
