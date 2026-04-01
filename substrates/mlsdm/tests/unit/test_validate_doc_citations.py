from pathlib import Path

from scripts.docs.validate_doc_citations import validate_doc_citations


def _write(tmp_path: Path, relative: str, content: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_unknown_citation_is_flagged(tmp_path: Path):
    bib = """
@article{known_key,
  author = {Doe, Jane},
  title = {Known work},
  year = {2024},
  doi = {10.1111/known}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib)
    _write(tmp_path, "docs/notes.md", "Some text [@missing_key].")
    errors = validate_doc_citations(tmp_path, foundation_docs=(), neuro_core_docs=())
    assert any("UNKNOWN CITATION" in e for e in errors), errors


def test_foundation_missing_citations_is_flagged(tmp_path: Path):
    bib = """
@article{known_key,
  author = {Doe, Jane},
  title = {Known work},
  year = {2024},
  doi = {10.1111/known}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib)
    _write(tmp_path, "docs/ARCHITECTURE_SPEC.md", "No citations here.")
    errors = validate_doc_citations(
        tmp_path, foundation_docs=("docs/ARCHITECTURE_SPEC.md",), neuro_core_docs=()
    )
    assert any("MISSING CITATIONS" in e for e in errors), errors


def test_valid_citations_pass(tmp_path: Path):
    bib = """
@article{known_key,
  author = {Doe, Jane},
  title = {Known work},
  year = {2024},
  doi = {10.1111/known}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib)
    _write(tmp_path, "docs/ARCHITECTURE_SPEC.md", "We cite [@known_key].")
    errors = validate_doc_citations(
        tmp_path, foundation_docs=("docs/ARCHITECTURE_SPEC.md",), neuro_core_docs=()
    )
    assert errors == [], errors


def test_neuro_core_freeform_citation_is_flagged(tmp_path: Path):
    bib = """
@article{known_key,
  author = {Doe, Jane},
  title = {Known work},
  year = {2024},
  doi = {10.1111/known}
}
"""
    _write(tmp_path, "docs/bibliography/REFERENCES.bib", bib)
    _write(tmp_path, "docs/NEURO_FOUNDATIONS.md", "Evidence from Doe, 2024.")
    errors = validate_doc_citations(
        tmp_path, foundation_docs=(), neuro_core_docs=("docs/NEURO_FOUNDATIONS.md",)
    )
    assert any("FREEFORM CITATION" in e for e in errors), errors
