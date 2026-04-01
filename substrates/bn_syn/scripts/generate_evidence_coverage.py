#!/usr/bin/env python3
"""Generate EVIDENCE_COVERAGE.md from claims.yml and bibliography.

This script produces a deterministic evidence coverage table showing
traceability for each claim in the registry.

Output: docs/EVIDENCE_COVERAGE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "claims" / "claims.yml"
BIB = ROOT / "bibliography" / "bnsyn.bib"
LOCK = ROOT / "bibliography" / "sources.lock"
OUTPUT = ROOT / "docs" / "EVIDENCE_COVERAGE.md"

DOI_RE = re.compile(r"doi\s*=\s*\{([^}]+)\}", re.IGNORECASE)
KEY_RE = re.compile(r"@\w+\{([^,]+),")


def parse_bibtex_dois(path: Path) -> dict[str, str]:
    """Extract bibkey -> DOI mapping from bibtex file."""
    text = path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    chunks = ["@" + c for c in text.split("@") if c.strip()]
    for c in chunks:
        key_match = KEY_RE.search(c)
        if not key_match:
            continue
        key = key_match.group(1).strip()
        doi_match = DOI_RE.search(c)
        doi = doi_match.group(1).strip() if doi_match else ""
        entries[key] = doi
    return entries


def parse_lock_entries(path: Path) -> dict[str, dict[str, str]]:
    """Extract bibkey -> DOI/NODOI and canonical URL from sources.lock."""
    result: dict[str, dict[str, str]] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        bibkey, rest = line.split("=", 1)
        parts = rest.split("::")
        if len(parts) >= 2:
            doi_or_nodoi = parts[0].strip()
            url = parts[1].strip()
            result[bibkey.strip()] = {"doi_or_nodoi": doi_or_nodoi, "url": url}
    return result


def format_paths(paths: list[str]) -> str:
    """Format paths as comma-separated backticked list."""
    return ", ".join(f"`{p}`" for p in paths)


def main() -> int:
    if not CLAIMS.exists():
        print(f"ERROR: Missing {CLAIMS}", file=sys.stderr)
        return 1

    data = yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))
    claims = data.get("claims", [])
    if not claims:
        print("ERROR: No claims found", file=sys.stderr)
        return 1

    bib_dois = parse_bibtex_dois(BIB) if BIB.exists() else {}
    lock_entries = parse_lock_entries(LOCK)

    lines = [
        "# Evidence Coverage",
        "",
        "| Claim ID | Tier | Normative | Status | Bibkey | DOI/URL | Spec Section | Implementation Paths | Verification Paths |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for c in claims:
        cid = str(c.get("id", ""))
        tier = str(c.get("tier", ""))
        normative = "true" if c.get("normative") else "false"
        status = str(c.get("status", ""))
        bibkey = str(c.get("bibkey", ""))
        spec_section = str(c.get("spec_section", ""))
        impl_paths = c.get("implementation_paths", [])
        ver_paths = c.get("verification_paths", [])

        # Get DOI from bib or fall back to lock URL
        doi_or_url = bib_dois.get(bibkey, "")
        if not doi_or_url:
            lock_entry = lock_entries.get(bibkey, {})
            doi_or_url = lock_entry.get("doi_or_nodoi", "")
            if doi_or_url == "NODOI":
                doi_or_url = lock_entry.get("url", "")

        impl_str = format_paths(impl_paths) if impl_paths else ""
        ver_str = format_paths(ver_paths) if ver_paths else ""

        lines.append(
            f"| {cid} | {tier} | {normative} | {status} | {bibkey} | {doi_or_url} | {spec_section} | {impl_str} | {ver_str} |"
        )

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[evidence-coverage] Generated {OUTPUT}")
    print(f"[evidence-coverage] Claims: {len(claims)}")
    print(f"[evidence-coverage] Tier-A: {sum(1 for c in claims if c.get('tier') == 'Tier-A')}")
    print(f"[evidence-coverage] Tier-S: {sum(1 for c in claims if c.get('tier') == 'Tier-S')}")
    print(f"[evidence-coverage] Normative: {sum(1 for c in claims if c.get('normative'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
