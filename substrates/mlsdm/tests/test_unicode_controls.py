from pathlib import Path

from scripts import check_no_unicode_controls


def test_detects_disallowed_controls(tmp_path: Path) -> None:
    target = tmp_path / "bad.svg"
    target.write_text("<svg>bad\u202e</svg>", encoding="utf-8")

    offenders = check_no_unicode_controls.find_offenders(tmp_path, ("*.svg",))

    assert len(offenders) == 1
    assert "U+202E" in offenders[0]


def test_passes_clean_files(tmp_path: Path) -> None:
    target = tmp_path / "good.md"
    target.write_text("# Clean\n", encoding="utf-8")

    offenders = check_no_unicode_controls.find_offenders(tmp_path, ("*.md",))

    assert offenders == []
