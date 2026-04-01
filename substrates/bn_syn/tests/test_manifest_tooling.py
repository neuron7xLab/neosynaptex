from __future__ import annotations

from pathlib import Path

from tools.manifest import generate


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_workflow_metrics_supports_yml_yaml_and_on_shapes(tmp_path: Path) -> None:
    workflows = tmp_path / ".github/workflows"
    _write(
        workflows / "_reusable_one.yml",
        "on:\n  workflow_call:\n",
    )
    _write(
        workflows / "list_trigger.yaml",
        "on: [workflow_dispatch, workflow_call]\n",
    )
    _write(
        workflows / "string_trigger.yml",
        "on: workflow_call\n",
    )
    _write(
        workflows / "other.yml",
        "on:\n  push:\n    branches: [main]\n",
    )

    total, reusable, workflow_call = generate._workflow_metrics(workflows)

    assert total == 4
    assert reusable == 1
    assert workflow_call == 3


def test_repo_fingerprint_is_path_invariant(tmp_path: Path, monkeypatch: object) -> None:
    def build_repo(root: Path) -> None:
        _write(root / "manifest/repo_manifest.yml", "manifest_version: '1.0'\n")
        _write(root / ".github/PR_GATES.yml", "version: '1'\nrequired_pr_gates: []\n")
        _write(
            root / "quality/coverage_gate.json",
            '{"minimum_percent": 99.0, "baseline_percent": 99.57}\n',
        )
        _write(
            root / "quality/mutation_baseline.json",
            '{"baseline_score": 0.0, "metrics": {"total_mutants": 103}}\n',
        )
        _write(root / ".github/workflows/a.yml", "on:\n  pull_request:\n")
        _write(root / ".github/workflows/b.yaml", "on: [workflow_call]\n")

    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    build_repo(repo_a)
    build_repo(repo_b)

    monkeypatch.setattr(generate, "ROOT", repo_a)
    fp_a = generate._repo_fingerprint()
    monkeypatch.setattr(generate, "ROOT", repo_b)
    fp_b = generate._repo_fingerprint()

    assert fp_a == fp_b


def test_ci_manifest_reference_count_respects_declared_scope(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    root = tmp_path / "repo"
    _write(root / ".github/workflows/ci.yml", "# ci_manifest.json\n")
    _write(root / "scripts/s.py", "# ci_manifest.json\n")
    _write(root / "docs/d.md", "ci_manifest.json\n")
    _write(root / "Makefile", "# ci_manifest.json\n")
    _write(root / "README.md", "ci_manifest.json\n")
    _write(root / "tools/ignored.py", "ci_manifest.json\n")

    monkeypatch.setattr(generate, "ROOT", root)

    assert generate._count_ci_manifest_references() == 5
