from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SHA_PIN = re.compile(r'^[^@]+@[0-9a-f]{40}$')


def test_workflow_actions_pinned_by_sha() -> None:
    policy = yaml.safe_load((REPO_ROOT / '.github' / 'ci_policy.yml').read_text(encoding='utf-8'))
    allow_unpinned = set(policy['actions'].get('allow_unpinned', []))
    violations: list[str] = []

    for wf in sorted((REPO_ROOT / '.github' / 'workflows').glob('*.yml')):
        for line in wf.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped.startswith('uses:'):
                continue
            action = stripped.split('uses:', 1)[1].strip().strip('"\'')
            if action.startswith('./') or action in allow_unpinned:
                continue
            if not SHA_PIN.match(action):
                violations.append(f'{wf.name}: {action}')

    assert violations == []
