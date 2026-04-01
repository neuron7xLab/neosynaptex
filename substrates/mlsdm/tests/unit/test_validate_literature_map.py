import textwrap
from pathlib import Path

from scripts.docs.validate_literature_map import validate_literature_map


def write_references(tmp_path: Path, keys: list[str]) -> None:
    bib_dir = tmp_path / "docs" / "bibliography"
    bib_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for key in keys:
        entries.append(
            f"""@article{{{key},
  title={{Title {key}}},
  author={{Author}},
  year={{2024}},
  url={{https://test.invalid/{key}}}
}}"""
        )
    (bib_dir / "REFERENCES.bib").write_text("\n\n".join(entries), encoding="utf-8")


def write_map(tmp_path: Path, content: str) -> Path:
    map_path = tmp_path / "docs" / "bibliography" / "LITERATURE_MAP.md"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return map_path


def test_valid_map_passes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    keys = ["alpha", "beta", "gamma", "delta"]
    write_references(tmp_path, keys)

    (tmp_path / "src" / "system" / "memory").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)

    map_path = write_map(
        tmp_path,
        """
        ## Memory Core
        paths: src/system/memory, tests/unit/
        citations: [@alpha] [@beta] [@gamma]
        rationale: ok

        ## Router
        paths: src/system/memory
        citations: [@beta] [@gamma] [@delta]
        rationale: ok
        """,
    )

    errors = validate_literature_map(tmp_path, map_path)
    assert errors == []


def test_unknown_citation_fails(tmp_path: Path) -> None:
    write_references(tmp_path, ["alpha", "beta", "gamma"])
    (tmp_path / "src" / "system").mkdir(parents=True)

    map_path = write_map(
        tmp_path,
        """
        ## Memory Core
        paths: src/system
        citations: [@alpha] [@beta] [@missing]
        rationale: ok
        """,
    )

    errors = validate_literature_map(tmp_path, map_path)
    assert any("unknown citation key" in err for err in errors)


def test_missing_paths_fails(tmp_path: Path) -> None:
    write_references(tmp_path, ["alpha", "beta", "gamma"])

    map_path = write_map(
        tmp_path,
        """
        ## Memory Core
        citations: [@alpha] [@beta] [@gamma]
        rationale: ok
        """,
    )

    errors = validate_literature_map(tmp_path, map_path)
    assert any("missing paths line" in err for err in errors)


def test_not_enough_citations_fails(tmp_path: Path) -> None:
    write_references(tmp_path, ["alpha", "beta", "gamma"])
    (tmp_path / "src" / "system").mkdir(parents=True)

    map_path = write_map(
        tmp_path,
        """
        ## Memory Core
        paths: src/system
        citations: [@alpha] [@beta]
        rationale: ok
        """,
    )

    errors = validate_literature_map(tmp_path, map_path)
    assert any("expected >=3 citations" in err for err in errors)


def test_nonexistent_path_fails(tmp_path: Path) -> None:
    write_references(tmp_path, ["alpha", "beta", "gamma"])
    (tmp_path / "src").mkdir(parents=True)

    map_path = write_map(
        tmp_path,
        """
        ## Memory Core
        paths: src/system
        citations: [@alpha] [@beta] [@gamma]
        rationale: ok
        """,
    )

    errors = validate_literature_map(tmp_path, map_path)
    assert any("path not found" in err for err in errors)
