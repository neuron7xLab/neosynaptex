from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tools.manifest import generate

pytestmark = pytest.mark.property


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@given(
    st.lists(
        st.tuples(
            st.booleans(),
            st.sampled_from(
                ["dict_call", "dict_other", "list_call", "list_other", "str_call", "str_other"]
            ),
        ),
        min_size=1,
        max_size=12,
    )
)
@settings(max_examples=80)
def test_workflow_metrics_property_matches_declared_triggers(
    entries: list[tuple[bool, str]],
) -> None:
    with TemporaryDirectory() as tmp_dir:
        workflows = Path(tmp_dir) / ".github/workflows"
        expected_reusable = 0
        expected_call = 0

        for idx, (is_reusable, mode) in enumerate(entries):
            suffix = ".yaml" if idx % 2 else ".yml"
            name = ("_reusable_" if is_reusable else "wf_") + f"{idx}{suffix}"
            path = workflows / name
            if mode == "dict_call":
                content = "on:\n  workflow_call:\n"
                expected_call += 1
            elif mode == "dict_other":
                content = "on:\n  push:\n    branches: [main]\n"
            elif mode == "list_call":
                content = "on: [workflow_dispatch, workflow_call]\n"
                expected_call += 1
            elif mode == "list_other":
                content = "on: [workflow_dispatch]\n"
            elif mode == "str_call":
                content = "on: workflow_call\n"
                expected_call += 1
            else:
                content = "on: workflow_dispatch\n"
            _write(path, content)
            if is_reusable:
                expected_reusable += 1

        total, reusable, workflow_call = generate._workflow_metrics(workflows)

        assert total == len(entries)
        assert reusable == expected_reusable
        assert workflow_call == expected_call


@given(st.lists(st.text(min_size=0, max_size=40), min_size=5, max_size=5))
@settings(max_examples=80)
def test_ci_manifest_reference_scope_fuzz(snippets: list[str]) -> None:
    with TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir) / "repo"
        scope_files = [
            root / ".github/workflows/ci.yml",
            root / "scripts/check.py",
            root / "docs/guide.md",
            root / "Makefile",
            root / "README.md",
        ]

        expected = 0
        for path, snippet in zip(scope_files, snippets):
            text = snippet + "\n"
            if len(snippet) % 2 == 0:
                text += "ci_manifest.json\n"
                expected += 1
            _write(path, text)

        _write(root / "tools/out_of_scope.py", "ci_manifest.json\n")

        old_root = generate.ROOT
        try:
            generate.ROOT = root
            assert generate._count_ci_manifest_references() == expected
        finally:
            generate.ROOT = old_root


@given(st.lists(st.sampled_from([".yml", ".yaml", ".txt", ".json"]), min_size=1, max_size=20))
@settings(max_examples=80)
def test_workflow_metrics_fuzz_ignores_non_yaml_extensions(exts: list[str]) -> None:
    with TemporaryDirectory() as tmp_dir:
        workflows = Path(tmp_dir) / ".github/workflows"
        expected_total = 0
        for idx, ext in enumerate(exts):
            name = f"wf_{idx}{ext}"
            text = "on: workflow_call\n" if idx % 2 == 0 else "on: workflow_dispatch\n"
            _write(workflows / name, text)
            if ext in {".yml", ".yaml"}:
                expected_total += 1

        total, _, _ = generate._workflow_metrics(workflows)
        assert total == expected_total
