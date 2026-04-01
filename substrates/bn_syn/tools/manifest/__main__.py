from __future__ import annotations

import argparse

from tools.manifest.generate import write_outputs
from tools.manifest.validate import validate_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Repository manifest tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("generate", help="Generate computed manifest artifacts")
    subparsers.add_parser("validate", help="Validate manifest artifacts against repository state")
    args = parser.parse_args()

    if args.command == "generate":
        write_outputs()
    elif args.command == "validate":
        validate_manifest()


if __name__ == "__main__":
    main()
