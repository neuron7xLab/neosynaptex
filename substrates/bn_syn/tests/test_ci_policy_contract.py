from __future__ import annotations

import tomllib
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_policy_schema_and_deterministic_commands() -> None:
    policy = yaml.safe_load((REPO_ROOT / '.github' / 'ci_policy.yml').read_text(encoding='utf-8'))
    assert isinstance(policy, dict)
    assert policy['protocol'] == 'DE-TF-2026.03'

    p0 = set(policy['tiers']['P0'])
    for gate in ('ruff', 'mypy', 'pytest', 'build'):
        assert gate in p0
        cmd = policy['tools'][gate]['cmd']
        assert cmd.startswith('python -m ')


def _normalize_requirement(requirement: str) -> str:
    normalized = requirement.split(';', maxsplit=1)[0].split('==', maxsplit=1)[0]
    normalized = normalized.split('[', maxsplit=1)[0].strip().lower()
    return normalized.replace('-', '_')


def test_p0_modules_declared_for_python_tools() -> None:
    policy = yaml.safe_load((REPO_ROOT / '.github' / 'ci_policy.yml').read_text(encoding='utf-8'))
    p0 = set(policy['tiers']['P0'])
    pyproject = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    optional = pyproject['project']['optional-dependencies']
    ci_deps = {_normalize_requirement(dep) for dep in optional['ci']}

    for name, tool in policy['tools'].items():
        if name not in p0:
            continue
        module_name = str(tool['module']).replace('-', '_')
        assert module_name in ci_deps, (
            f"P0 tool module '{module_name}' missing from [project.optional-dependencies].ci"
        )


def test_p0_modules_match_python_module_commands() -> None:
    policy = yaml.safe_load((REPO_ROOT / '.github' / 'ci_policy.yml').read_text(encoding='utf-8'))
    p0 = set(policy['tiers']['P0'])

    for name, tool in policy['tools'].items():
        if name not in p0:
            continue
        module_name = str(tool['module']).replace('-', '_')
        cmd = str(tool['cmd'])
        assert cmd.startswith('python -m ')
        assert cmd.removeprefix('python -m ').split()[0].replace('-', '_') == module_name
