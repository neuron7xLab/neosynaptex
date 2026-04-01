from __future__ import annotations

import json
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _job_names(workflow_path: Path) -> set[str]:
    parsed = yaml.safe_load(workflow_path.read_text(encoding='utf-8'))
    jobs = parsed.get('jobs', {}) if isinstance(parsed, dict) else {}
    return set(jobs.keys()) if isinstance(jobs, dict) else set()


def test_required_checks_manifest_schema() -> None:
    manifest = json.loads((REPO_ROOT / '.github' / 'required_checks.json').read_text(encoding='utf-8'))
    assert isinstance(manifest, dict)
    assert 'required_checks' in manifest
    assert isinstance(manifest['required_checks'], list)
    assert all(isinstance(x, str) for x in manifest['required_checks'])


def test_required_checks_match_workflow_jobs() -> None:
    manifest = json.loads((REPO_ROOT / '.github' / 'required_checks.json').read_text(encoding='utf-8'))
    workflow_jobs = _job_names(REPO_ROOT / '.github' / 'workflows' / 'pr_gate.yml')
    missing = sorted(set(manifest['required_checks']) - workflow_jobs)
    assert missing == []


def test_enforce_in_ci_enabled() -> None:
    policy = yaml.safe_load((REPO_ROOT / '.github' / 'ci_policy.yml').read_text(encoding='utf-8'))
    assert policy['required_checks']['enforce_in_ci'] is True

    workflow = (REPO_ROOT / '.github' / 'workflows' / 'pr_gate.yml').read_text(encoding='utf-8')
    assert 'tests/test_required_checks_manifest.py' in workflow
