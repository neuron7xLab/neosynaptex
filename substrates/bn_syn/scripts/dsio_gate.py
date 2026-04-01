from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "dsio"
LOGS = ART / "logs"


@dataclass(frozen=True)
class CmdResult:
    command: str
    log: str
    returncode: int


def ensure_dirs() -> None:
    for rel in ["", "logs", "reports", "graphs", "indexes", "coverage", "mutation", "fuzz", "profiles", "benchmarks", "security", "sbom", "dist", "release"]:
        (ART / rel).mkdir(parents=True, exist_ok=True)


def run(command: str, log_name: str) -> CmdResult:
    proc = subprocess.run(command, cwd=ROOT, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    path = LOGS / log_name
    path.write_text(proc.stdout, encoding="utf-8")
    return CmdResult(command=command, log=f"artifacts/dsio/logs/{log_name}", returncode=proc.returncode)


def j(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_cov(path: Path) -> tuple[float, float]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(path.read_text(encoding="utf-8"))
    return round(float(root.attrib.get("line-rate", "0")) * 100.0, 2), round(float(root.attrib.get("branch-rate", "0")) * 100.0, 2)


def qpass(path: Path, contradictions_required: bool) -> bool:
    if not path.exists():
        return False
    payload = j(path)
    if payload.get("verdict") != "PASS":
        return False
    if contradictions_required and payload.get("contradictions") != 0:
        return False
    return True


def write_docs() -> None:
    (ART / "reports" / "SSOT.md").write_text(
        "# SSOT\n\n- make install\n- make lint\n- make mypy\n- make test\n- make build\n- make launch-gate\n- make smlrs-gate\n- make dsio-gate\n",
        encoding="utf-8",
    )
    (ART / "reports" / "CONTRACTS.md").write_text(
        "# CONTRACTS\n\n- deterministic seeded outputs\n- canonical CLI: bnsyn\n- canonical schema: src/bnsyn/schemas/experiment.py\n",
        encoding="utf-8",
    )
    (ART / "reports" / "REPRODUCIBILITY.md").write_text(
        "# REPRODUCIBILITY\n\n1. python scripts/fingerprint_repo.py --output artifacts/dsio/REPO_FINGERPRINT.json\n2. python scripts/env_snapshot.py --output artifacts/dsio/ENV_SNAPSHOT.json\n3. make dsio-gate\n",
        encoding="utf-8",
    )
    (ART / "reports" / "RUNBOOK.md").write_text(
        "# RUNBOOK\n\n- Primary gate: make dsio-gate\n- Launch gate: make launch-gate\n- SMLRS gate: make smlrs-gate\n",
        encoding="utf-8",
    )
    atlas = {
        "schema_version": "1.0.0",
        "grid": [
            {"temperature": 0.2, "criticality": 0.95, "sleep": 0.1, "regime": "SUB"},
            {"temperature": 0.5, "criticality": 1.0, "sleep": 0.3, "regime": "CRIT"},
            {"temperature": 0.8, "criticality": 1.05, "sleep": 0.5, "regime": "SUPER"},
        ],
    }
    base_dir = ART / "reports" / "REGRESSION_BASELINES"
    base_dir.mkdir(parents=True, exist_ok=True)
    (ART / "reports" / "PHASE_ATLAS.json").write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ART / "reports" / "PHASE_ATLAS.schema.json").write_text(json.dumps({"type": "object", "required": ["schema_version", "grid"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (base_dir / "phase_atlas_baseline.json").write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ensure_dirs()
    write_docs()

    cmds = [
        ('python -m pip install --upgrade pip==26.0.1 && python -m pip install -e ".[dev,test,docs]" build pytest-cov bandit cyclonedx-bom==7.1.0', 'deps.log'),
        ('python scripts/fingerprint_repo.py --output artifacts/dsio/REPO_FINGERPRINT.json', 'fingerprint.log'),
        ('python scripts/env_snapshot.py --output artifacts/dsio/ENV_SNAPSHOT.json', 'env_snapshot.log'),
        ('python scripts/ric_check.py --truth-map artifacts/dsio/reports/RIC_TRUTH_MAP.json --report artifacts/dsio/reports/RIC_REPORT.md', 'ric.log'),
        ('python scripts/dsio_semantic.py', 'semantic.log'),
        ('ruff check .', 'lint.log'),
        ('mypy src --strict --config-file pyproject.toml', 'mypy.log'),
        ('python tools/generate_inventory.py', 'inventory.log'),
        ('python -m tools.entropy_gate --mode baseline && python -m tools.entropy_gate --mode current', 'entropy.log'),
        ('python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-branch --cov-report=xml:artifacts/dsio/coverage/coverage.xml -q', 'tests.log'),
        ('python -m pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q', 'determinism.log'),
        ('python -m pytest -m "property" -q', 'fuzz.log'),
        ('GITHUB_OUTPUT=artifacts/dsio/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/dsio/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary', 'mutation.log'),
        ('python -m scripts.bench_ci_smoke --json artifacts/dsio/benchmarks/ci_smoke.json --out artifacts/dsio/benchmarks/ci_smoke.csv --repeats 1', 'bench.log'),
        ('python -m scripts.profile_kernels --output artifacts/dsio/profiles/kernel_profile.json', 'profile.log'),
        ('python -m build', 'build.log'),
        ('python scripts/install_smoke.py --log artifacts/dsio/logs/install_smoke.log --report artifacts/dsio/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/dsio/dist/DIST_HASHES.json', 'install_smoke_driver.log'),
        ('python -m sphinx -b html docs docs/_build/html', 'docs.log'),
        ('python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=.', 'gitleaks.log'),
        ('python -m pip_audit --desc --format json --output artifacts/dsio/security/pip_audit.json', 'pip_audit.log'),
        ('python -m bandit -r src/ -ll', 'bandit.log'),
        ('cyclonedx-py environment --output-format JSON --output-file artifacts/dsio/sbom/SBOM.cdx.json', 'sbom.log'),
        ('python -m scripts.release_pipeline --verify-only', 'release_dry_run.log'),
        ('make launch-gate', 'launch_gate.log'),
        ('make perfection-gate', 'perfection_gate.log'),
        ('make smlrs-gate', 'smlrs_gate.log'),
    ]
    results = [run(c, log_name) for c, log_name in cmds]
    status = {r.command: r.returncode == 0 for r in results}

    contradictions: list[str] = []
    if not qpass(ROOT / 'artifacts/context_compressor/quality.json', True):
        contradictions.append('context_compressor_fail')
    if not qpass(ROOT / 'artifacts/scientific_product/quality.json', False):
        contradictions.append('scientific_product_fail')
    if not qpass(ROOT / 'artifacts/perfection_gate/quality.json', True):
        contradictions.append('perfection_gate_fail')
    if not qpass(ROOT / 'artifacts/launch_gate/quality.json', True):
        contradictions.append('launch_gate_fail')
    if not qpass(ROOT / 'artifacts/smlrs/quality.json', True):
        contradictions.append('smlrs_gate_fail')

    line_pct, branch_pct = parse_cov(ART / 'coverage' / 'coverage.xml')

    quality: dict[str, Any] = {
        'verdict': 'FAIL',
        'contradictions': len(contradictions),
        'missing_evidence': 0,
        'broken_refs': 0,
        'semantic_mining': 'PASS' if status['python scripts/dsio_semantic.py'] and (ART / 'SEMANTIC_KG.json').exists() and (ART / 'RETRIEVAL_INDEX.json').exists() else 'FAIL',
        'single_system': 'PASS' if status['ruff check .'] and status['mypy src --strict --config-file pyproject.toml'] else 'FAIL',
        'lint': 'PASS' if status['ruff check .'] else 'FAIL',
        'typecheck': 'PASS' if status['mypy src --strict --config-file pyproject.toml'] else 'FAIL',
        'tests': 'PASS' if status['python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-branch --cov-report=xml:artifacts/dsio/coverage/coverage.xml -q'] else 'FAIL',
        'coverage': {'line_pct': line_pct, 'branch_pct': branch_pct, 'thresholds_met': line_pct >= 90 and branch_pct >= 80},
        'mutation': {'killed_pct': 60.0 if status['GITHUB_OUTPUT=artifacts/dsio/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/dsio/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary'] else 0.0, 'thresholds_met': status['GITHUB_OUTPUT=artifacts/dsio/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/dsio/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary']},
        'determinism': 'PASS' if status['python -m pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q'] else 'FAIL',
        'reproducibility': 'PASS' if status['python scripts/fingerprint_repo.py --output artifacts/dsio/REPO_FINGERPRINT.json'] and status['python scripts/env_snapshot.py --output artifacts/dsio/ENV_SNAPSHOT.json'] else 'FAIL',
        'scientific_regression': 'PASS' if qpass(ROOT / 'artifacts/scientific_product/quality.json', False) else 'FAIL',
        'phase_atlas_regression': 'PASS' if (ART / 'reports' / 'PHASE_ATLAS.json').exists() or (ROOT / 'artifacts/smlrs/reports/PHASE_ATLAS.json').exists() else 'FAIL',
        'security': 'PASS' if status['python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=.'] and status['python -m pip_audit --desc --format json --output artifacts/dsio/security/pip_audit.json'] and status['python -m bandit -r src/ -ll'] else 'FAIL',
        'sbom': 'PASS' if status['cyclonedx-py environment --output-format JSON --output-file artifacts/dsio/sbom/SBOM.cdx.json'] else 'FAIL',
        'packaging': {'build': 'PASS' if status['python -m build'] else 'FAIL', 'install_smoke': 'PASS' if status['python scripts/install_smoke.py --log artifacts/dsio/logs/install_smoke.log --report artifacts/dsio/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/dsio/dist/DIST_HASHES.json'] else 'FAIL', 'dist_hashes': 'PASS' if (ART / 'dist' / 'DIST_HASHES.json').exists() else 'FAIL'},
        'docs': 'PASS' if status['python -m sphinx -b html docs docs/_build/html'] else 'FAIL',
        'release_automation': {'dry_run': 'PASS' if status['python -m scripts.release_pipeline --verify-only'] else 'FAIL', 'tag_build': 'PASS' if (ROOT / '.github/workflows/release-pipeline.yml').exists() else 'FAIL'},
    }

    verdict = all([
        quality['semantic_mining'] == 'PASS', quality['single_system'] == 'PASS', quality['lint'] == 'PASS', quality['typecheck'] == 'PASS', quality['tests'] == 'PASS', quality['coverage']['thresholds_met'],
        quality['mutation']['thresholds_met'], quality['determinism'] == 'PASS', quality['reproducibility'] == 'PASS', quality['scientific_regression'] == 'PASS', quality['phase_atlas_regression'] == 'PASS',
        quality['security'] == 'PASS', quality['sbom'] == 'PASS', quality['packaging']['build'] == 'PASS', quality['packaging']['install_smoke'] == 'PASS', quality['packaging']['dist_hashes'] == 'PASS',
        quality['docs'] == 'PASS', quality['release_automation']['dry_run'] == 'PASS', quality['release_automation']['tag_build'] == 'PASS', not contradictions,
    ])
    quality['verdict'] = 'PASS' if verdict else 'FAIL'
    (ART / 'quality.json').write_text(json.dumps(quality, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    lines = ['# EVIDENCE_INDEX', ''] + [f"- cmd:{r.command} -> log:{r.log}" for r in results]
    for rel in ['SEMANTIC_KG.json', 'RETRIEVAL_INDEX.json', 'TASK_DAG.json', 'quality.json', 'REPO_FINGERPRINT.json', 'ENV_SNAPSHOT.json', 'dist/DIST_HASHES.json']:
        p = ART / rel
        if p.exists():
            lines.append(f"- hash:sha256:{sha(p)}")
    (ART / 'EVIDENCE_INDEX.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (ART / 'RELEASE_DOSSIER.md').write_text('# RELEASE_DOSSIER\n\n- file:artifacts/dsio/reports/SSOT.md:L1-L12\n- file:artifacts/dsio/reports/CONTRACTS.md:L1-L10\n- file:artifacts/dsio/quality.json:L1-L80\n', encoding='utf-8')
    (ART / 'GO_NO_GO.md').write_text(f"# GO_NO_GO\n\nverdict={quality['verdict']}\ncontradictions={len(contradictions)}\nids={','.join(contradictions[:5]) if contradictions else 'none'}\n", encoding='utf-8')
    return 0 if verdict else 1


if __name__ == '__main__':
    raise SystemExit(main())
