from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_ALLOWED_TOKENS = re.compile(r"\b[a-zA-Z_]\w*\b")


def _marker_selected(markexpr: str, marker: str) -> bool:
    if not markexpr:
        return True

    def _replace_identifier(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in {"and", "or", "not", "True", "False"}:
            return token
        return "True" if token == marker else "False"

    bool_expr = _ALLOWED_TOKENS.sub(_replace_identifier, markexpr)
    parsed = ast.parse(bool_expr, mode="eval")
    return bool(eval(compile(parsed, "<markexpr>", "eval"), {"__builtins__": {}}, {}))


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    if "tests/properties" not in collection_path.as_posix():
        return False
    markexpr = (config.option.markexpr or "").strip()
    return not _marker_selected(markexpr, "property")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    errors: list[str] = []
    for item in items:
        path = Path(str(item.fspath)).resolve().as_posix()
        in_validation_dir = "tests/validation" in path
        in_property_dir = "tests/properties" in path
        has_validation_marker = item.get_closest_marker("validation") is not None
        has_property_marker = item.get_closest_marker("property") is not None

        if in_validation_dir and not has_validation_marker:
            errors.append(f"Missing @pytest.mark.validation for {item.nodeid}")
        if not in_validation_dir and has_validation_marker:
            errors.append(f"Validation marker used outside tests/validation: {item.nodeid}")

        if in_property_dir and not has_property_marker:
            errors.append(f"Missing @pytest.mark.property for {item.nodeid}")
        if not in_property_dir and has_property_marker:
            errors.append(f"Property marker used outside tests/properties: {item.nodeid}")

    if errors:
        raise pytest.UsageError("\n".join(errors))
