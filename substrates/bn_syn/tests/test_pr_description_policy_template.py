from __future__ import annotations

from pathlib import Path


def test_pull_request_template_contains_required_policy_sections() -> None:
    template = Path('.github/pull_request_template.md').read_text(encoding='utf-8').lower()
    required_sections = [
        'what changed',
        'why',
        'risk',
        'evidence',
        'how to test',
    ]

    missing = [section for section in required_sections if section not in template]
    assert not missing, f'Missing required PR-policy sections: {missing}'
