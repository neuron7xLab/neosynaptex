#!/usr/bin/env python3
"""
Validate BN-Syn bibliography SSOT:
- bnsyn.bib entries include DOI for Tier-A sources
- mapping.yml is well-formed and references existing bibkeys
- sources.lock lines are syntactically valid and SHA256 matches LOCK_STRING
- tiers and claim mappings are consistent across claims/mapping
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ssot_rules import RULE_IDS, assert_rule_ids_match  # noqa: E402

BIB = ROOT / "bibliography" / "bnsyn.bib"
LOCK = ROOT / "bibliography" / "sources.lock"
MAP = ROOT / "bibliography" / "mapping.yml"
CLAIMS = ROOT / "claims" / "claims.yml"

DOI_RE = re.compile(r"doi\s*=\s*\{([^}]+)\}", re.IGNORECASE)
KEY_RE = re.compile(r"@\w+\{([^,]+),")
FIELD_RE = re.compile(r"(?im)^\s*(\w+)\s*=\s*[\{\"]([^\"}]+)[\}\"]\s*,?")
URL_IN_HOWPUBLISHED_RE = re.compile(r"\\url\{([^}]+)\}?")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_TIERS = {"Tier-A", "Tier-S", "Tier-B", "Tier-C"}


class ValidationError(Exception):
    """Raised when bibliography validation invariants are violated."""



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


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError("mapping.yml must be a YAML mapping")
    out: dict[str, dict[str, str]] = {}
    for clm, v in data.items():
        if not isinstance(clm, str) or not clm.startswith("CLM-"):
            raise ValidationError(f"Invalid CLM key: {clm!r}")
        if not isinstance(v, dict):
            raise ValidationError(f"{clm}: value must be mapping with keys bibkey/tier/section")
        for req in ("bibkey", "tier", "section"):
            if req not in v:
                raise ValidationError(f"{clm}: missing required field {req}")
        bibkey = v["bibkey"]
        tier = v["tier"]
        if not isinstance(bibkey, str) or not bibkey:
            raise ValidationError(f"{clm}: bibkey must be non-empty string")
        if not isinstance(tier, str) or tier not in ALLOWED_TIERS:
            raise ValidationError(f"{clm}: tier must be one of {sorted(ALLOWED_TIERS)}")
        out[clm] = {"bibkey": bibkey, "tier": tier, "section": str(v["section"])}
    return out


def load_claims(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError("claims.yml must be a YAML mapping")
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValidationError("claims.yml must contain a non-empty claims list")
    out: dict[str, dict[str, str]] = {}
    for entry in claims:
        if not isinstance(entry, dict):
            raise ValidationError("claims.yml claim entry must be a mapping")
        cid = entry.get("id")
        if not isinstance(cid, str) or not cid.startswith("CLM-"):
            raise ValidationError(f"claims.yml invalid claim id: {cid!r}")
        if cid in out:
            raise ValidationError(f"claims.yml duplicate claim id: {cid}")
        out[cid] = {
            "tier": str(entry.get("tier", "")),
            "normative": bool(entry.get("normative", False)),
            "bibkey": str(entry.get("bibkey", "")),
            "spec_section": str(entry.get("spec_section", "")),
        }
    return out


def parse_lock(path: Path) -> list[dict[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValidationError(f"sources.lock invalid line (missing '='): {line}")
        bibkey, rest = line.split("=", 1)
        parts = rest.split("::")
        if len(parts) != 5:
            raise ValidationError(
                f"sources.lock invalid field count for {bibkey}: expected 5 '::' fields, got {len(parts)}"
            )
        doi_or_nodoi, url, f3, f4, sha = [p.strip() for p in parts]
        if not sha.startswith("sha256:"):
            raise ValidationError(f"sources.lock {bibkey} missing sha256: prefix")
        rows.append(
            {
                "bibkey": bibkey.strip(),
                "doi_or_nodoi": doi_or_nodoi,
                "url": url,
                "f3": f3,
                "f4": f4,
                "sha": sha.replace("sha256:", "", 1),
            }
        )
    return rows


def fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def main() -> int:
    assert_rule_ids_match(RULE_IDS)

    for p in (BIB, LOCK, MAP, CLAIMS):
        if not p.exists():
            return fail(f"missing required file: {p}")

    try:
        bib = parse_bibtex(BIB)
        mapping = load_mapping(MAP)
        claims = load_claims(CLAIMS)
        lock_rows = parse_lock(LOCK)
    except ValidationError as exc:
        return fail(str(exc))

    lock_by_key = {r["bibkey"]: r for r in lock_rows}
    missing_lock = set(bib.keys()) - set(lock_by_key.keys())
    if missing_lock:
        return fail(f"sources.lock missing bibkeys: {sorted(missing_lock)}")

    missing_in_mapping = set(claims.keys()) - set(mapping.keys())
    extra_in_mapping = set(mapping.keys()) - set(claims.keys())
    if missing_in_mapping:
        return fail(f"mapping.yml missing claim IDs: {sorted(missing_in_mapping)}")
    if extra_in_mapping:
        return fail(f"mapping.yml has unknown claim IDs: {sorted(extra_in_mapping)}")

    for clm, v in mapping.items():
        bk = v["bibkey"]
        tier = v["tier"]
        section = v["section"]
        if bk not in bib:
            return fail(f"{clm} references unknown bibkey: {bk}")
        claim = claims.get(clm)
        if not claim:
            return fail(f"{clm} missing in claims.yml")
        if claim["tier"] != tier:
            return fail(f"{clm} tier mismatch (claims={claim['tier']}, mapping={tier})")
        if claim["bibkey"] != bk:
            return fail(f"{clm} bibkey mismatch (claims={claim['bibkey']}, mapping={bk})")
        if claim["spec_section"] != section:
            return fail(
                f"{clm} spec_section mismatch (claims={claim['spec_section']}, mapping={section})"
            )
        if tier == "Tier-A" and not claim["normative"]:
            return fail(f"{clm} Tier-A requires normative=true in claims.yml")
        if tier in {"Tier-S", "Tier-B", "Tier-C"} and claim["normative"]:
            return fail(f"{clm} {tier} requires normative=false in claims.yml")
        if tier == "Tier-A":
            doi = bib[bk]["doi"]
            if not doi:
                return fail(f"{clm} is Tier-A but bibkey {bk} has no DOI")
        if tier == "Tier-S":
            lock_entry = lock_by_key.get(bk)
            if not lock_entry:
                return fail(f"{clm} Tier-S bibkey {bk} missing in sources.lock")
            if lock_entry["doi_or_nodoi"] != "NODOI":
                return fail(f"{clm} Tier-S bibkey {bk} must be NODOI in sources.lock")
            if not lock_entry["url"]:
                return fail(f"{clm} Tier-S bibkey {bk} missing canonical URL in sources.lock")
            if not lock_entry["f4"]:
                return fail(f"{clm} Tier-S bibkey {bk} missing retrieved_date in sources.lock")

    for bk, entry in lock_by_key.items():
        sha = entry["sha"]
        if not HEX64_RE.match(sha):
            return fail(f"sources.lock {bk} has invalid SHA256 (must be 64 lowercase hex): {sha}")
        doi_or_nodoi = entry["doi_or_nodoi"]
        if doi_or_nodoi == "NODOI":
            lock_string = f"{bk}=NODOI::{entry['url']}::{entry['f3']}::{entry['f4']}"
        else:
            lock_string = f"{bk}={doi_or_nodoi}::{entry['url']}::{entry['f3']}::{entry['f4']}"
        expected = sha256_hex(lock_string)
        if expected != sha:
            return fail(
                f"sources.lock {bk} SHA mismatch\n  expected: {expected}\n  actual:   {sha}"
            )

    print("OK: bibliography SSOT validated.")
    print(f"  Bibkeys: {len(bib)}")
    print(f"  Mapping entries: {len(mapping)}")
    print(f"  Claim IDs: {len(claims)}")
    print(f"  Lock entries: {len(lock_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
