#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / "bibliography" / "bnsyn.bib"
LOCK = ROOT / "bibliography" / "sources.lock"
MAP = ROOT / "bibliography" / "mapping.yml"

KEY_RE = re.compile(r"@\w+\{([^,]+),")
FIELD_RE = re.compile(r"(?im)^\s*(\w+)\s*=\s*[\{\"]([^\"}]+)[\}\"]\s*,?")
DOI_RE = re.compile(r"doi\s*=\s*\{([^}]+)\}", re.IGNORECASE)
URL_IN_HOWPUBLISHED_RE = re.compile(r"\\url\{([^}]+)\}")


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_bibtex(path: Path) -> dict[str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    chunks = ["@" + c for c in text.split("@") if c.strip()]
    for c in chunks:
        key_match = KEY_RE.search(c)
        if not key_match:
            continue
        key = key_match.group(1).strip()
        fields = {k.lower(): v.strip() for k, v in FIELD_RE.findall(c)}
        doi_match = DOI_RE.search(c)
        doi = doi_match.group(1).strip() if doi_match else fields.get("doi", "")
        url = fields.get("url", "")
        howpublished = fields.get("howpublished", "")
        if not url and howpublished:
            url_match = URL_IN_HOWPUBLISHED_RE.search(howpublished)
            if url_match:
                url = url_match.group(1).strip()
        entries[key] = {
            "doi": doi,
            "url": url,
            "year": fields.get("year", ""),
            "journal": fields.get("journal", ""),
            "publisher": fields.get("publisher", ""),
        }
    return entries


def parse_lock(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        bibkey, rest = line.split("=", 1)
        parts = rest.split("::")
        if len(parts) != 5:
            continue
        doi_or_nodoi, url, f3, f4, sha = [p.strip() for p in parts]
        rows[bibkey.strip()] = {
            "doi_or_nodoi": doi_or_nodoi,
            "url": url,
            "f3": f3,
            "f4": f4,
            "sha": sha,
        }
    return rows


def load_mapping(path: Path) -> dict[str, str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("mapping.yml must be a YAML mapping")
    tiers: dict[str, str] = {}
    for clm, entry in data.items():
        if not isinstance(entry, dict):
            raise SystemExit(f"{clm}: mapping entry must be a mapping")
        bibkey = str(entry.get("bibkey", "")).strip()
        tier = str(entry.get("tier", "")).strip()
        if not bibkey or not tier:
            raise SystemExit(f"{clm}: mapping entry missing bibkey or tier")
        if bibkey in tiers and tiers[bibkey] != tier:
            raise SystemExit(f"Bibkey {bibkey} has conflicting tiers in mapping")
        tiers[bibkey] = tier
    return tiers


def format_tier_a(bibkey: str, entry: dict[str, str]) -> str:
    doi = entry["doi"].lower()
    url = entry["url"]
    year = entry["year"]
    journal = entry["journal"] or entry["publisher"]
    if not (doi and url and year and journal):
        raise SystemExit(f"Tier-A bibkey {bibkey} missing doi/url/year/journal")
    lock_string = f"{bibkey}={doi}::{url}::{year}::{journal}"
    return f"{lock_string}::sha256:{sha256_hex(lock_string)}"


def format_tier_s(bibkey: str, entry: dict[str, str], existing: dict[str, str]) -> str:
    url = entry["url"] or existing.get("url", "")
    publisher = existing.get("f3", entry.get("publisher", ""))
    retrieved = existing.get("f4", "")
    if not (url and publisher and retrieved):
        raise SystemExit(f"Tier-S bibkey {bibkey} missing url/publisher/retrieved_date")
    lock_string = f"{bibkey}=NODOI::{url}::{publisher}::{retrieved}"
    return f"{lock_string}::sha256:{sha256_hex(lock_string)}"


def main() -> int:
    bib = parse_bibtex(BIB)
    tiers = load_mapping(MAP)
    existing_lock = parse_lock(LOCK)

    lines = [
        "# /bibliography/sources.lock",
        "# Lockfile for BN-Syn Bibliography",
        "#",
        "# Tier-A LOCK_STRING = '<bibkey>=<doi>::<canonical_url>::<year>::<publisher_or_journal>'",
        "# Tier-S LOCK_STRING = '<bibkey>=NODOI::<canonical_url>::<publisher>::<retrieved_date>'",
        "# SHA256 is computed over LOCK_STRING (UTF-8) and stored as 64 lowercase hex.",
        "# Format:",
        "#   Tier-A: <bibkey>=<doi>::<canonical_url>::<year>::<publisher_or_journal>::sha256:<hex>",
        "#   Tier-S: <bibkey>=NODOI::<canonical_url>::<publisher>::<retrieved_date>::sha256:<hex>",
        "",
    ]

    new_entries = []
    for bibkey in sorted(bib.keys()):
        tier = tiers.get(bibkey)
        if not tier:
            raise SystemExit(f"Bibkey {bibkey} missing tier in mapping.yml")
        if tier == "Tier-A":
            new_entries.append(format_tier_a(bibkey, bib[bibkey]))
        elif tier == "Tier-S":
            new_entries.append(format_tier_s(bibkey, bib[bibkey], existing_lock.get(bibkey, {})))
        else:
            raise SystemExit(f"Bibkey {bibkey} has unsupported tier {tier}")

    lines.extend(new_entries)
    new_text = "\n".join(lines) + "\n"

    old_lines = (
        [
            ln
            for ln in LOCK.read_text(encoding="utf-8").splitlines()
            if ln and not ln.startswith("#")
        ]
        if LOCK.exists()
        else []
    )
    new_lines = [ln for ln in new_entries]

    added = len([ln for ln in new_lines if ln not in old_lines])
    removed = len([ln for ln in old_lines if ln not in new_lines])
    changed = len(new_lines) - len(set(new_lines).intersection(set(old_lines)))

    LOCK.write_text(new_text, encoding="utf-8")

    print("Rebuilt sources.lock")
    print(f"  entries: {len(new_entries)}")
    print(f"  added: {added}")
    print(f"  removed: {removed}")
    print(f"  changed: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
