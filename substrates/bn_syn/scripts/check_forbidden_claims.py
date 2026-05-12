from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [ROOT / "docs", ROOT / "benchmarks", ROOT / "README.md", ROOT / "PULL_REQUEST_TEMPLATE.md"]
FORBIDDEN = [
    "proves intelligence",
    "proves consciousness",
    "human-ai fusion",
    "validated neurobiological model",
    "10x proven",
    "universal law",
    "γ=1 everywhere",
    "substrate-independent law",
    "confirmed universal exponent",
]
ALLOWLIST_HINTS = ["forbidden_claims", "claim boundary", "forbidden phrases"]
ALLOWLIST_PATHS = {"docs/specs/pfc_coherent_induction_v2.md"}


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for item in SCAN_DIRS:
        if item.is_file():
            out.append(item)
            continue
        if item.exists():
            out.extend(p for p in item.rglob("*.md") if p.is_file())
            out.extend(p for p in item.rglob("*.yaml") if p.is_file())
            out.extend(p for p in item.rglob("*.yml") if p.is_file())
            out.extend(p for p in item.rglob("*.json") if p.is_file())
    return out


def main() -> int:
    violations: list[str] = []
    for path in _iter_files():
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel in ALLOWLIST_PATHS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()
        if any(hint in lowered for hint in ALLOWLIST_HINTS):
            continue
        for phrase in FORBIDDEN:
            for line in lowered.splitlines():
                if phrase in line:
                    if any(tok in line for tok in ("forbidden", "do not", "must not", "reject", "blocked")):
                        continue
                    violations.append(f"{path.relative_to(ROOT)}: {phrase}")
    if violations:
        print("forbidden_claims_detected")
        for violation in violations:
            print(violation)
        return 1
    print("forbidden_claims_check_passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
