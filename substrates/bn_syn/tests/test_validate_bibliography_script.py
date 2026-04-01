from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate_bibliography as vb  # noqa: E402


def test_parse_bibtex_extracts_url_from_howpublished(tmp_path: Path) -> None:
    bib = (
        "@article{KeyOne,\n"
        "  doi = {10.1000/xyz123},\n"
        "  howpublished = {\\url{https://example.org/paper}},\n"
        "  year = {2024},\n"
        "}\n"
    )
    path = tmp_path / "bnsyn.bib"
    path.write_text(bib, encoding="utf-8")

    entries = vb.parse_bibtex(path)

    assert entries["KeyOne"]["doi"] == "10.1000/xyz123"
    assert entries["KeyOne"]["url"] == "https://example.org/paper"
    assert entries["KeyOne"]["year"] == "2024"


def test_load_mapping_rejects_unknown_tier(tmp_path: Path) -> None:
    mapping = "CLM-0001:\n  bibkey: Example2024\n  tier: Tier-Z\n  section: 1.2\n"
    path = tmp_path / "mapping.yml"
    path.write_text(mapping, encoding="utf-8")

    with pytest.raises(vb.ValidationError, match="tier must be one of"):
        vb.load_mapping(path)


def test_load_claims_rejects_duplicate_ids(tmp_path: Path) -> None:
    claims = (
        "claims:\n"
        "  - id: CLM-0001\n"
        "    tier: Tier-A\n"
        "    normative: true\n"
        "    bibkey: Example2024\n"
        "    spec_section: 1.2\n"
        "  - id: CLM-0001\n"
        "    tier: Tier-A\n"
        "    normative: true\n"
        "    bibkey: Example2024\n"
        "    spec_section: 1.2\n"
    )
    path = tmp_path / "claims.yml"
    path.write_text(claims, encoding="utf-8")

    with pytest.raises(vb.ValidationError, match="duplicate claim id"):
        vb.load_claims(path)


def test_parse_lock_accepts_valid_rows(tmp_path: Path) -> None:
    lock_string = "Example2024=10.1000/xyz123::https://example.org::f3::f4"
    sha = vb.sha256_hex(lock_string)
    content = f"Example2024=10.1000/xyz123::https://example.org::f3::f4::sha256:{sha}\n"
    path = tmp_path / "sources.lock"
    path.write_text(content, encoding="utf-8")

    rows = vb.parse_lock(path)

    assert rows == [
        {
            "bibkey": "Example2024",
            "doi_or_nodoi": "10.1000/xyz123",
            "url": "https://example.org",
            "f3": "f3",
            "f4": "f4",
            "sha": sha,
        }
    ]
