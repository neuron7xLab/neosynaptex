from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from .contracts import ContractError, load_task_contract
from .controller import AOCController


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aoc", description="Adaptive Orchestration Controller")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run deterministic local AOC")
    run.add_argument("--config", required=True)
    run.add_argument("--out-dir", default=None)
    run.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command != "run":
        return 1
    try:
        payload = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        contract = load_task_contract(payload)
    except (OSError, yaml.YAMLError, KeyError, ValueError, ContractError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True))
        return 2

    run_dir = Path(args.out_dir or payload.get("output_dir", "aoc_output"))
    verdict = AOCController(contract, run_dir).run()
    print(json.dumps(verdict, sort_keys=True))
    return 0 if verdict.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
