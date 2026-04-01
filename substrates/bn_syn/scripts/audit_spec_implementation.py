from __future__ import annotations

import pathlib
import re
from typing import Iterable

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs" / "SPEC.md"
MAP_PATH = ROOT / "docs" / "spec_to_code.yml"

COMPONENT_RE = re.compile(r"^##\s+(P\d-\d+):\s*(.+)$")


def _read_spec_components(lines: Iterable[str]) -> list[tuple[str, str]]:
    components: list[tuple[str, str]] = []
    for line in lines:
        match = COMPONENT_RE.match(line.strip())
        if match:
            components.append((match.group(1), match.group(2).strip()))
    return components


def _has_validation_marker(text: str) -> bool:
    return "pytest.mark.validation" in text or "pytestmark = pytest.mark.validation" in text


def main() -> int:
    if not SPEC_PATH.exists():
        print(f"Missing SPEC: {SPEC_PATH}")
        return 1
    if not MAP_PATH.exists():
        print(f"Missing spec_to_code map: {MAP_PATH}")
        return 1

    spec_components = _read_spec_components(SPEC_PATH.read_text().splitlines())
    if len(spec_components) != 12:
        print(f"Expected 12 spec components, found {len(spec_components)}")
        for cid, name in spec_components:
            print(f"  - {cid}: {name}")
        return 1

    components = yaml.safe_load(MAP_PATH.read_text()) or {}
    if not isinstance(components, dict):
        print("spec_to_code.yml must be a mapping of component IDs")
        return 1

    errors: list[str] = []
    for comp_id, comp_name in spec_components:
        entry = components.get(comp_id)
        if entry is None:
            errors.append(f"Missing mapping for {comp_id} ({comp_name})")
            continue
        impl_paths = entry.get("implementation_paths") or []
        test_paths = entry.get("test_paths") or []
        claim_ids = entry.get("claim_ids") or []
        if not impl_paths:
            errors.append(f"{comp_id} missing implementation_paths")
        if not test_paths:
            errors.append(f"{comp_id} missing test_paths")
        if not claim_ids:
            errors.append(f"{comp_id} missing claim_ids")
        for rel in impl_paths:
            path = ROOT / rel
            if not path.exists():
                errors.append(f"{comp_id} implementation missing: {rel}")
        for rel in test_paths:
            path = ROOT / rel
            if not path.exists():
                errors.append(f"{comp_id} test missing: {rel}")
                continue
            text = path.read_text()
            if "tests/validation" in rel.replace("\\", "/"):
                if not _has_validation_marker(text):
                    errors.append(
                        f"{comp_id} validation test missing pytest.mark.validation: {rel}"
                    )
            else:
                if _has_validation_marker(text):
                    errors.append(f"{comp_id} smoke test incorrectly marked validation: {rel}")

    if errors:
        print("Spec implementation audit failed:")
        for err in errors:
            print(f" - {err}")
        return 1

    print("Spec implementation audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
