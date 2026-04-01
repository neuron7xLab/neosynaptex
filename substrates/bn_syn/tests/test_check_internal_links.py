from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_internal_links


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example.com", None),
        ("#local-anchor", None),
        ("docs/INDEX.md", Path("docs/INDEX.md")),
        ("docs/INDEX.md#section", Path("docs/INDEX.md")),
    ],
)
def test_normalize_target(raw: str, expected: Path | None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / "README.md"
    doc.write_text("# readme\n", encoding="utf-8")
    monkeypatch.chdir(repo)

    result = check_internal_links._normalize_target(raw, doc)
    if expected is None:
        assert result is None
    else:
        assert result == (repo / expected).resolve()


def test_check_internal_links_reports_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "README.md").write_text("[Index](docs/INDEX.md)\n", encoding="utf-8")
    (repo / "docs/INDEX.md").write_text("[Missing](./MISSING.md)\n", encoding="utf-8")
    (repo / "docs/TRACEABILITY.md").write_text("# Traceability\n", encoding="utf-8")

    monkeypatch.chdir(repo)
    monkeypatch.setattr(
        check_internal_links,
        "TARGET_DOCS",
        [Path("README.md"), Path("docs/INDEX.md"), Path("docs/TRACEABILITY.md")],
    )

    with pytest.raises(SystemExit, match="BROKEN_LINK"):
        check_internal_links.check_internal_links()
