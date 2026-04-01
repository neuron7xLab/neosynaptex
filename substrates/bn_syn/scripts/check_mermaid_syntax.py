"""Static Mermaid safety checks for GitHub-rendered Markdown."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_TYPES = {"flowchart", "sequenceDiagram", "stateDiagram-v2", "classDiagram"}
TARGET_FILES = [
    Path("README.md"),
    Path("docs/INDEX.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("docs/STATUS.md"),
    Path("docs/DOC_DEBT.md"),
]
UNSAFE = set("#*<>`{}|")
PAIRINGS = {"(": ")", "[": "]", "{": "}"}


def extract_mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, flags=re.DOTALL)


def check_balanced(block: str) -> bool:
    stack: list[str] = []
    quote = False
    for ch in block:
        if ch == '"':
            quote = not quote
            continue
        if quote:
            continue
        if ch in PAIRINGS:
            stack.append(ch)
        elif ch in PAIRINGS.values():
            if not stack:
                return False
            open_ch = stack.pop()
            if PAIRINGS[open_ch] != ch:
                return False
    return (not stack) and (not quote)


def check_unquoted_labels(block: str) -> bool:
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if '"' in stripped:
            continue
        if "[" in stripped and "]" in stripped:
            label = stripped.split("[", 1)[1].rsplit("]", 1)[0]
            if any(ch in UNSAFE for ch in label):
                return False
    return True


def main() -> int:
    for path in TARGET_FILES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for block in extract_mermaid_blocks(text):
            first = next((ln.strip() for ln in block.splitlines() if ln.strip()), "")
            if first.split(" ", 1)[0] not in ALLOWED_TYPES:
                print(f"ERROR:{path}:unsupported_mermaid_type")
                return 1
            if not check_balanced(block):
                print(f"ERROR:{path}:unbalanced_mermaid")
                return 1
            if not check_unquoted_labels(block):
                print(f"ERROR:{path}:unsafe_unquoted_label")
                return 1
    print("MERMAID_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
