from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

import yaml

from scripts.validate_required_status_contexts import expected_required_status_contexts

ROOT = Path(__file__).resolve().parents[1]


def build_payload(pr_gates_path: Path, workflows_dir: Path) -> dict[str, object]:
    contexts = expected_required_status_contexts(pr_gates_path, workflows_dir)
    return {"version": "1", "required_status_contexts": contexts}


def sync_required_status_contexts(
    contexts_path: Path,
    pr_gates_path: Path,
    workflows_dir: Path,
    *,
    check: bool,
) -> int:
    payload = build_payload(pr_gates_path, workflows_dir)
    rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)

    current = contexts_path.read_text(encoding="utf-8") if contexts_path.exists() else ""
    if current == rendered:
        print(f"OK: {contexts_path} already up to date ({len(payload['required_status_contexts'])} contexts)")
        return 0

    if check:
        print(
            f"DRIFT: {contexts_path} is out of date. Run: python -m scripts.sync_required_status_contexts"
        )
        return 2

    contexts_path.write_text(rendered, encoding="utf-8")
    print(f"UPDATED: {contexts_path} with {len(payload['required_status_contexts'])} contexts")
    return 0


def main(argv: list[str]) -> int:
    parser = ArgumentParser(description="Sync .github/REQUIRED_STATUS_CONTEXTS.yml with PR gate workflows")
    parser.add_argument("--check", action="store_true", help="Fail if file would change")
    args = parser.parse_args(argv[1:])

    return sync_required_status_contexts(
        contexts_path=ROOT / ".github/REQUIRED_STATUS_CONTEXTS.yml",
        pr_gates_path=ROOT / ".github/PR_GATES.yml",
        workflows_dir=ROOT / ".github/workflows",
        check=args.check,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
