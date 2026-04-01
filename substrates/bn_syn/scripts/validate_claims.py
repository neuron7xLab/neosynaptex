#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ssot_rules import RULE_IDS, assert_rule_ids_match  # noqa: E402

REQUIRED_TOP_KEYS = {"version", "claims"}
REQUIRED_CLAIM_KEYS = {
    "id",
    "statement",
    "status",
    "tier",
    "normative",
    "source",
    "locator",
    "action",
    "notes",
    "bibkey",
    "spec_section",
    "implementation_paths",
    "verification_paths",
}

ALLOWED_STATUS = {"PROVEN", "UNPROVEN"}
ALLOWED_TIER = {"Tier-A", "Tier-B", "Tier-C", "Tier-S"}
ALLOWED_ACTION = {"KEEP", "REMOVE", "DOWNGRADE", "CORRECT"}


def fail(msg: str) -> None:
    print(f"[claims-gate] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("mapping.yml must be a YAML mapping")
    out: dict[str, dict[str, str]] = {}
    for clm, v in data.items():
        if not isinstance(v, dict):
            fail(f"{clm}: mapping entry must be a mapping")
        out[clm] = {
            "bibkey": str(v.get("bibkey", "")).strip(),
            "section": str(v.get("section", "")).strip(),
            "tier": str(v.get("tier", "")).strip(),
        }
    return out


def ensure_paths_exist(paths: list[str]) -> None:
    for p in paths:
        target = ROOT / p
        if not target.exists():
            fail(f"Referenced path does not exist: {p}")


def ensure_path_prefix(paths: list[str], allowed_prefixes: tuple[str, ...], label: str) -> None:
    for p in paths:
        if not p.startswith(allowed_prefixes):
            fail(f"{label} path must live in {allowed_prefixes}: {p}")


def main() -> int:
    assert_rule_ids_match(RULE_IDS)

    ledger = ROOT / "claims" / "claims.yml"
    mapping_path = ROOT / "bibliography" / "mapping.yml"
    if not ledger.exists():
        fail("claims/claims.yml not found")
    if not mapping_path.exists():
        fail("bibliography/mapping.yml not found")

    data = yaml.safe_load(ledger.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("claims.yml must be a YAML mapping")

    missing = REQUIRED_TOP_KEYS - set(data.keys())
    if missing:
        fail(f"claims.yml missing top keys: {sorted(missing)}")

    claims = data.get("claims", [])
    if not isinstance(claims, list) or not claims:
        fail("claims.yml has empty or invalid 'claims' list")

    mapping = load_mapping(mapping_path)

    ids: set[str] = set()
    for c in claims:
        if not isinstance(c, dict):
            fail("Claim entry is not a dict")
        miss = REQUIRED_CLAIM_KEYS - set(c.keys())
        if miss:
            fail(f"Claim {c.get('id', '<no-id>')} missing keys: {sorted(miss)}")
        cid = str(c["id"]).strip()
        if not re.match(r"^CLM-\d{4}$", cid):
            fail(f"Invalid claim id format: {cid}")
        if cid in ids:
            fail(f"Duplicate claim id: {cid}")
        ids.add(cid)

        status = str(c["status"]).strip().upper()
        tier = str(c["tier"]).strip()
        action = str(c["action"]).strip().upper()
        normative = bool(c["normative"])
        bibkey = str(c["bibkey"]).strip()
        spec_section = str(c["spec_section"]).strip()
        implementation_paths = c["implementation_paths"]
        verification_paths = c["verification_paths"]

        if status not in ALLOWED_STATUS:
            fail(f"{cid}: invalid status {status}")
        if tier not in ALLOWED_TIER:
            fail(f"{cid}: invalid tier {tier}")
        if action not in ALLOWED_ACTION:
            fail(f"{cid}: invalid action {action}")

        if tier == "Tier-A" and not normative:
            fail(f"{cid}: Tier-A requires normative=true")
        if tier in {"Tier-S", "Tier-B", "Tier-C"} and normative:
            fail(f"{cid}: {tier} requires normative=false")

        if normative:
            if status != "PROVEN":
                fail(f"{cid}: normative=true requires status=PROVEN")
            if tier != "Tier-A":
                fail(f"{cid}: normative=true requires tier=Tier-A")
            if not str(c["source"]).strip() or str(c["source"]).strip().lower() == "unresolved":
                fail(f"{cid}: normative=true requires source")
            if not str(c["locator"]).strip() or str(c["locator"]).strip().lower() == "unresolved":
                fail(f"{cid}: normative=true requires locator")

        if not isinstance(implementation_paths, list) or not implementation_paths:
            fail(f"{cid}: implementation_paths must be a non-empty list")
        if not isinstance(verification_paths, list) or not verification_paths:
            fail(f"{cid}: verification_paths must be a non-empty list")

        impl_paths = [str(p) for p in implementation_paths]
        ver_paths = [str(p) for p in verification_paths]
        ensure_paths_exist(impl_paths)
        ensure_paths_exist(ver_paths)
        ensure_path_prefix(impl_paths, ("src/", "scripts/"), f"{cid} implementation")
        ensure_path_prefix(ver_paths, ("tests/", "scripts/"), f"{cid} verification")

        mapping_entry = mapping.get(cid)
        if not mapping_entry:
            fail(f"{cid}: missing mapping entry in bibliography/mapping.yml")
        if mapping_entry["bibkey"] != bibkey:
            fail(f"{cid}: bibkey mismatch (claims={bibkey}, mapping={mapping_entry['bibkey']})")
        if mapping_entry["section"] != spec_section:
            fail(
                f"{cid}: spec_section mismatch (claims={spec_section}, mapping={mapping_entry['section']})"
            )
        if mapping_entry["tier"] != tier:
            fail(f"{cid}: tier mismatch (claims={tier}, mapping={mapping_entry['tier']})")

    print(
        f"[claims-gate] OK: {len(claims)} claims validated; {sum(1 for c in claims if c.get('normative'))} normative."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
