import json
from pathlib import Path

from scripts.validate_bibliography import (
    check_bibtex,
    check_identifiers_against_bib,
    load_identifiers_json,
)


def _write(tmp_path: Path, relative: str, content: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_duplicate_doi_is_flagged(tmp_path):
    bib_content = """
@article{dup_one,
  author = {Doe, Jane},
  title = {First work},
  year = {2024},
  doi = {10.1234/dupdoi}
}

@article{dup_two,
  author = {Smith, John},
  title = {Second work},
  year = {2024},
  doi = {10.1234/dupdoi}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib_content)

    errors, _, _ = check_bibtex(tmp_path)

    assert any("Duplicate DOI" in err for err in errors), errors


def test_identifiers_missing_fields_are_reported(tmp_path):
    bib_content = """
@article{foo2024_bar,
  author = {Doe, Jane},
  title = {Offline validator check},
  year = {2024},
  doi = {10.4242/foo.bar}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib_content)

    identifiers_payload = {
        "foo2024_bar": {
            "canonical_id_type": "doi",
            "canonical_id": "",
            "canonical_url": "",
            "verified_on": "2025-12-30",
            "verification_method": "crossref",
            "frozen_metadata": {
                "title": "Offline validator check",
                "year": "2024",
                "first_author_family": "Doe",
                "venue": "Journal",
            },
        }
    }
    _write(
        tmp_path,
        "docs/bibliography/metadata/identifiers.json",
        json.dumps(identifiers_payload, indent=2),
    )

    id_load_errors, identifiers = load_identifiers_json(tmp_path)
    assert not id_load_errors

    bib_errors, _, entries = check_bibtex(tmp_path)
    assert not bib_errors

    identifier_errors = check_identifiers_against_bib(entries, identifiers)
    assert any("missing canonical_id" in err for err in identifier_errors), (
        f"missing canonical_id not reported: {identifier_errors}"
    )
    assert any("canonical_url must use https" in err for err in identifier_errors), (
        f"canonical_url https check missing: {identifier_errors}"
    )


def test_duplicate_normalized_work_is_flagged(tmp_path):
    bib_content = """
@article{first_key,
  author = {Smith, John},
  title = {Attention Is All You Need},
  year = {2017},
  doi = {10.1111/unique-one}
}

@article{second_key,
  author = {Smith, John},
  title = {Attention is all you need},
  year = {2017},
  doi = {10.2222/unique-two}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib_content)

    errors, _, _ = check_bibtex(tmp_path)

    assert any("Duplicate work detected" in err for err in errors), errors
