from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.manifest import generate, validate


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_min_repo(root: Path) -> None:
    _write(
        root / "manifest/repo_manifest.yml",
        "\n".join(
            [
                'manifest_version: "1.0"',
                "required_pr_gates:",
                '  source: ".github/PR_GATES.yml"',
                f'  sha256: "{hashlib.sha256((root / ".github/PR_GATES.yml").read_bytes()).hexdigest()}"',
                "invariants:",
                "  - id: INV-001",
                '    statement: "s"',
                '    enforcement: "e"',
                '    evidence_kind: "artifact"',
                "metrics:",
                "  - workflow_total",
                "policies:",
                "  generated_files_are_readonly: true",
                "  drift_is_failure: true",
                "  deterministic_sorting: true",
                "  generated_files:",
                '    - ".github/REPO_MANIFEST.md"',
                '    - "manifest/repo_manifest.computed.json"',
                "evidence_rules:",
                "  accepted_pointer_formats:",
                '    - "path:line-span"',
                '    - "artifact"',
            ]
        )
        + "\n",
    )
    _write(
        root / "manifest/repo_manifest.schema.json",
        (Path("manifest/repo_manifest.schema.json")).read_text(),
    )
    _write(root / ".github/PR_GATES.yml", "version: '1'\nrequired_pr_gates: []\n")
    _write(
        root / "quality/coverage_gate.json",
        '{"minimum_percent": 99.0, "baseline_percent": 99.57}\n',
    )
    _write(
        root / "quality/mutation_baseline.json",
        '{"baseline_score": 0.0, "metrics": {"total_mutants": 103}}\n',
    )
    _write(root / ".github/workflows/ci.yml", "on:\n  workflow_call:\n")
    _write(root / "scripts/noop.py", "print('ok')\n")
    _write(root / "docs/readme.md", "ok\n")
    _write(root / "Makefile", "all:\n\t@true\n")
    _write(root / "README.md", "ok\n")


def _patch_roots(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(generate, "ROOT", root)
    monkeypatch.setattr(generate, "SSOT_PATH", root / "manifest/repo_manifest.yml")
    monkeypatch.setattr(generate, "SCHEMA_PATH", root / "manifest/repo_manifest.schema.json")
    monkeypatch.setattr(generate, "COMPUTED_PATH", root / "manifest/repo_manifest.computed.json")
    monkeypatch.setattr(generate, "RENDERED_PATH", root / ".github/REPO_MANIFEST.md")

    monkeypatch.setattr(validate, "ROOT", root)
    monkeypatch.setattr(validate, "SSOT_PATH", root / "manifest/repo_manifest.yml")
    monkeypatch.setattr(validate, "SCHEMA_PATH", root / "manifest/repo_manifest.schema.json")
    monkeypatch.setattr(validate, "COMPUTED_PATH", root / "manifest/repo_manifest.computed.json")


def test_validate_fails_on_computed_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    _write(root / ".github/PR_GATES.yml", "version: '1'\nrequired_pr_gates: []\n")
    _build_min_repo(root)
    _patch_roots(monkeypatch, root)

    generate.write_outputs()

    computed_path = root / "manifest/repo_manifest.computed.json"
    payload = json.loads(computed_path.read_text(encoding="utf-8"))
    payload["metrics"]["workflow_total"] = 999
    computed_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="Computed manifest drift detected"):
        validate.validate_manifest()


def test_generate_summary_hashes_match_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "repo"
    _write(root / ".github/PR_GATES.yml", "version: '1'\nrequired_pr_gates: []\n")
    _build_min_repo(root)
    _patch_roots(monkeypatch, root)

    generate.write_outputs()
    out = capsys.readouterr().out.strip()

    assert out.startswith("manifest.generate ")
    fields = dict(item.split("=", 1) for item in out.split()[1:])
    computed_text = (root / "manifest/repo_manifest.computed.json").read_text(encoding="utf-8")
    rendered_text = (root / ".github/REPO_MANIFEST.md").read_text(encoding="utf-8")
    assert fields["computed_sha256"] == hashlib.sha256(computed_text.encode("utf-8")).hexdigest()
    assert fields["rendered_sha256"] == hashlib.sha256(rendered_text.encode("utf-8")).hexdigest()


def test_validate_fails_when_ci_manifest_references_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    _write(root / ".github/PR_GATES.yml", "version: '1'\nrequired_pr_gates: []\n")
    _build_min_repo(root)
    _write(root / "README.md", "ci_manifest.json\n")
    _patch_roots(monkeypatch, root)

    generate.write_outputs()

    with pytest.raises(SystemExit, match="ci_manifest.json references detected"):
        validate.validate_manifest()


def test_repo_fingerprint_invariant_to_file_creation_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def build(root: Path, ordered: bool) -> None:
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
        items = [
            (".github/workflows/b.yaml", "on: [workflow_call]\n"),
            (".github/workflows/a.yml", "on:\n  pull_request:\n"),
        ]
        seq = items if ordered else list(reversed(items))
        for rel, txt in seq:
            _write(root / rel, txt)

    a = tmp_path / "a"
    b = tmp_path / "b"
    build(a, ordered=True)
    build(b, ordered=False)

    monkeypatch.setattr(generate, "ROOT", a)
    fp_a = generate._repo_fingerprint()
    monkeypatch.setattr(generate, "ROOT", b)
    fp_b = generate._repo_fingerprint()

    assert fp_a == fp_b
