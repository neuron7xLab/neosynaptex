from __future__ import annotations

from pathlib import Path


def test_no_env_dependent_skips_in_unit() -> None:
    """Fail if unit tests hide behind environment-dependent skips."""
    unit_dir = Path(__file__).resolve().parent.parent / "unit"
    offenders: list[str] = []
    forbidden_tokens = ("pytest.skip(", "pytest.importorskip(", "importorskip(")

    for path in unit_dir.rglob("*.py"):
        with path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                if any(token in line for token in forbidden_tokens) and "# allow-skip:" not in line:
                    relative_path = path.relative_to(unit_dir.parent)
                    offenders.append(f"{relative_path}:{lineno}: {line.strip()}")

    assert not offenders, (
        "Env-dependent skip/importorskip found in unit tests:\n" + "\n".join(offenders)
    )
