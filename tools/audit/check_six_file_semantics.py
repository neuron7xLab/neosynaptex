#!/usr/bin/env python3
"""Semantic quality gate for Six-File Methodology artifacts.

This check complements presence checks by validating required structural semantics.
Outputs machine-readable report and returns non-zero on failure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path('.')
OUT = ROOT / 'artifacts/audit/six_file_semantics_report.json'


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def main() -> int:
    checks: list[dict[str, str]] = []

    # 01_problem.md: must include one-sentence problem and explicit falsification section
    p01 = _read('docs/research/01_problem.md')
    has_fals = 'Falsification Condition' in p01
    has_problem = bool(re.search(r'Проблема\s*:', p01))
    checks.append({'check': 'PRE-01.problem_statement', 'status': 'PASS' if has_problem else 'FAIL'})
    checks.append({'check': 'PRE-01.falsification_condition', 'status': 'PASS' if has_fals else 'FAIL'})

    # 02_contract.yaml: must have inputs/outputs/boundaries non-empty
    c02 = yaml.safe_load(_read('docs/research/02_contract.yaml')) or {}
    for key in ('inputs', 'outputs', 'boundaries'):
        ok = key in c02 and bool(c02[key])
        checks.append({'check': f'PRE-02.{key}', 'status': 'PASS' if ok else 'FAIL'})

    # 03_invariants.yaml: ids and pass_condition required
    i03 = yaml.safe_load(_read('docs/research/03_invariants.yaml')) or {}
    invs = i03.get('invariants', [])
    required_ids = {'PRE-03', 'MATH-01', 'VAL-01'}
    found_ids = {x.get('id') for x in invs if isinstance(x, dict)}
    checks.append({'check': 'INVARIANTS.required_ids', 'status': 'PASS' if required_ids.issubset(found_ids) else 'FAIL'})
    pass_conditions_ok = all(isinstance(x, dict) and x.get('pass_condition') for x in invs)
    checks.append({'check': 'INVARIANTS.pass_condition', 'status': 'PASS' if pass_conditions_ok else 'FAIL'})

    # 04_test_plan.md: must contain red->green and adversarial
    p04 = _read('docs/research/04_test_plan.md')
    checks.append({'check': 'VAL-01.red_green', 'status': 'PASS' if 'Red' in p04 and 'Green' in p04 else 'FAIL'})
    checks.append({'check': 'VAL-03.adversarial', 'status': 'PASS' if 'Adversarial' in p04 else 'FAIL'})

    # 05_governance.md: must include Human Impact + Rollback + CI Failure Mapping
    p05 = _read('docs/research/05_governance.md')
    checks.append({'check': 'GOV-01.human_impact', 'status': 'PASS' if 'Human Impact' in p05 else 'FAIL'})
    checks.append({'check': 'GOV-02.rollback', 'status': 'PASS' if 'Rollback' in p05 else 'FAIL'})
    checks.append({'check': 'GOV-03.ci_mapping', 'status': 'PASS' if 'CI Failure Mapping' in p05 else 'FAIL'})

    # 06_change_plan.md: require numbered plan with at least 3 steps
    p06 = _read('docs/research/06_change_plan.md')
    steps = re.findall(r'^\d+\.', p06, flags=re.MULTILINE)
    checks.append({'check': 'IMPL-PLAN.min_steps_3', 'status': 'PASS' if len(steps) >= 3 else 'FAIL'})

    status = 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL'
    report = {
        'check_id': 'SEM-01',
        'protocol_id': 'NEOSYNAPTEX-PROTOCOL-v1.1',
        'status': status,
        'checks': checks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(OUT)
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
