from __future__ import annotations

from pathlib import Path


def test_no_time_sleep_in_unit_tests() -> None:
    unit_dir = Path(__file__).resolve().parent.parent / "unit"
    offenders: list[str] = []

    for path in unit_dir.rglob("*.py"):
        with path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                if "time.sleep(" in line and "# allow-sleep:" not in line:
                    relative_path = path.relative_to(unit_dir.parent)
                    offenders.append(f"{relative_path}:{lineno}: {line.strip()}")

    assert not offenders, "time.sleep found in unit tests without waiver:\n" + "\n".join(
        offenders
    )
