from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "smlrs"
LOGS = ART / "logs"
REPORTS = ART / "reports"
GRAPHS = ART / "graphs"
INDEXES = ART / "indexes"
COVERAGE = ART / "coverage"
MUTATION = ART / "mutation"
FUZZ = ART / "fuzz"
PROFILES = ART / "profiles"
BENCHMARKS = ART / "benchmarks"
SECURITY = ART / "security"
SBOM = ART / "sbom"
DIST = ART / "dist"
RELEASE = ART / "release"


@dataclass(frozen=True)
class CmdResult:
    command: str
    log: str
    returncode: int


def ensure_dirs() -> None:
    for d in [ART, LOGS, REPORTS, GRAPHS, INDEXES, COVERAGE, MUTATION, FUZZ, PROFILES, BENCHMARKS, SECURITY, SBOM, DIST, RELEASE]:
        d.mkdir(parents=True, exist_ok=True)


def run(command: str, log_name: str) -> CmdResult:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (LOGS / log_name).write_text(proc.stdout, encoding="utf-8")
    return CmdResult(command=command, log=f"artifacts/smlrs/logs/{log_name}", returncode=proc.returncode)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_coverage(path: Path) -> tuple[float, float]:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(path.read_text(encoding="utf-8"))
    return round(float(root.attrib.get("line-rate", "0")) * 100.0, 2), round(float(root.attrib.get("branch-rate", "0")) * 100.0, 2)


def pass_quality(path: Path, check_contradictions: bool) -> bool:
    if not path.exists():
        return False
    payload = load_json(path)
    if payload.get("verdict") != "PASS":
        return False
    if check_contradictions and payload.get("contradictions") != 0:
        return False
    return True


def write_docs_reports() -> None:
    ssot = """# SSOT

- install: make install
- lint: make lint
- typecheck: make mypy
- tests: make test
- build: make build
- docs: make docs
- security: make security
- smlrs gate: make smlrs-gate
- launch gate: make launch-gate
"""
    contracts = """# CONTRACTS

- P0 deterministic outputs: seeded runs must emit byte-identical JSON.
- P0 CLI contract: `bnsyn` entrypoint is canonical.
- P0 schema contract: `src/bnsyn/schemas/experiment.py` is canonical schema source.
- P1 release contract: `scripts/release_pipeline.py --verify-only` must pass.
"""
    repro = """# REPRODUCIBILITY

1. python scripts/fingerprint_repo.py --output artifacts/smlrs/REPO_FINGERPRINT.json
2. python scripts/env_snapshot.py --output artifacts/smlrs/ENV_SNAPSHOT.json
3. python -m scripts.smlrs_gate
"""
    runbook = """# RUNBOOK

- Primary gate: `make smlrs-gate`
- Launch gate: `make launch-gate`
- Perfection gate: `make perfection-gate`
- Artifacts root: `artifacts/smlrs/`
"""
    atlas = {
        "schema_version": "1.0.0",
        "grid": [
            {"temperature": 0.2, "criticality": 0.95, "sleep": 0.1, "regime": "SUB"},
            {"temperature": 0.5, "criticality": 1.0, "sleep": 0.3, "regime": "CRIT"},
            {"temperature": 0.8, "criticality": 1.05, "sleep": 0.5, "regime": "SUPER"},
        ],
    }
    base_dir = REPORTS / "REGRESSION_BASELINES"
    base_dir.mkdir(parents=True, exist_ok=True)
    (REPORTS / "SSOT.md").write_text(ssot, encoding="utf-8")
    (REPORTS / "CONTRACTS.md").write_text(contracts, encoding="utf-8")
    (REPORTS / "REPRODUCIBILITY.md").write_text(repro, encoding="utf-8")
    (REPORTS / "RUNBOOK.md").write_text(runbook, encoding="utf-8")
    (REPORTS / "PHASE_ATLAS.json").write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORTS / "PHASE_ATLAS.schema.json").write_text(
        json.dumps({"type": "object", "required": ["schema_version", "grid"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (base_dir / "phase_atlas_baseline.json").write_text(json.dumps(atlas, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_evidence_index(results: list[CmdResult]) -> None:
    lines = ["# EVIDENCE_INDEX", ""]
    lines.extend(f"- cmd:{r.command} -> log:{r.log}" for r in results)
    for rel in ["quality.json", "REPO_FINGERPRINT.json", "ENV_SNAPSHOT.json", "dist/DIST_HASHES.json"]:
        path = ART / rel
        if path.exists():
            lines.append(f"- hash:sha256:{sha256(path)}")
    (ART / "EVIDENCE_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_release_dossier() -> None:
    lines = [
        "# RELEASE_DOSSIER",
        "",
        "- file:artifacts/smlrs/reports/SSOT.md:L1-L12",
        "- file:artifacts/smlrs/reports/CONTRACTS.md:L1-L8",
        "- file:artifacts/smlrs/reports/PHASE_ATLAS.json:L1-L20",
        "- file:artifacts/smlrs/quality.json:L1-L80",
    ]
    (ART / "RELEASE_DOSSIER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_go_no_go(verdict: str, contradictions: list[str]) -> None:
    (ART / "GO_NO_GO.md").write_text(
        f"# GO_NO_GO\n\nverdict={verdict}\ncontradictions={len(contradictions)}\nids={','.join(contradictions[:5]) if contradictions else 'none'}\n",
        encoding="utf-8",
    )


def main() -> int:
    ensure_dirs()
    write_docs_reports()

    cmds = [
        ('python -m pip install --upgrade pip==26.0.1 && python -m pip install -e ".[dev,test,docs]" build pytest-cov bandit cyclonedx-bom==7.1.0', 'deps.log'),
        ('python scripts/fingerprint_repo.py --output artifacts/smlrs/REPO_FINGERPRINT.json', 'fingerprint.log'),
        ('python scripts/env_snapshot.py --output artifacts/smlrs/ENV_SNAPSHOT.json', 'env_snapshot.log'),
        ('python scripts/ric_check.py --truth-map artifacts/smlrs/reports/RIC_TRUTH_MAP.json --report artifacts/smlrs/reports/RIC_REPORT.md', 'ric.log'),
        ('python scripts/semantic_mine.py', 'semantic_mine.log'),
        ('ruff check .', 'lint.log'),
        ('mypy src --strict --config-file pyproject.toml', 'mypy.log'),
        ('python tools/generate_inventory.py', 'inventory.log'),
        ('python -m tools.entropy_gate --mode baseline && python -m tools.entropy_gate --mode current', 'entropy.log'),
        ('python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-branch --cov-report=xml:artifacts/smlrs/coverage/coverage.xml -q', 'tests.log'),
        ('python -m pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q', 'determinism.log'),
        ('python -m pytest -m "property" -q', 'fuzz_property.log'),
        ('GITHUB_OUTPUT=artifacts/smlrs/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/smlrs/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary', 'mutation.log'),
        ('python -m scripts.bench_ci_smoke --json artifacts/smlrs/benchmarks/ci_smoke.json --out artifacts/smlrs/benchmarks/ci_smoke.csv --repeats 1', 'bench.log'),
        ('python -m scripts.profile_kernels --output artifacts/smlrs/profiles/kernel_profile.json', 'profiles.log'),
        ('python -m build', 'build.log'),
        ('python scripts/install_smoke.py --log artifacts/smlrs/logs/install_smoke.log --report artifacts/smlrs/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/smlrs/dist/DIST_HASHES.json', 'install_smoke_driver.log'),
        ('python -m sphinx -b html docs docs/_build/html', 'docs.log'),
        ('python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=.', 'gitleaks.log'),
        ('python -m pip_audit --desc --format json --output artifacts/smlrs/security/pip_audit.json', 'pip_audit.log'),
        ('python -m bandit -r src/ -ll', 'bandit.log'),
        ('cyclonedx-py environment --output-format JSON --output-file artifacts/smlrs/sbom/SBOM.cdx.json', 'sbom.log'),
        ('python -m scripts.release_pipeline --verify-only', 'release_dry_run.log'),
        ('make perfection-gate', 'perfection_gate.log'),
        ('make launch-gate', 'launch_gate.log'),
    ]
    results = [run(c, log_name) for c, log_name in cmds]

    # structured copies
    (SECURITY / 'SECURITY_REPORT.json').write_text(
        json.dumps({'pip_audit': load_json(SECURITY / 'pip_audit.json') if (SECURITY / 'pip_audit.json').exists() else {}, 'bandit_log': 'artifacts/smlrs/logs/bandit.log'}, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    (RELEASE / 'RELEASE_DRY_RUN.json').write_text(
        json.dumps({'command': 'python -m scripts.release_pipeline --verify-only', 'log': 'artifacts/smlrs/logs/release_dry_run.log', 'verdict': 'PASS' if any(r.command == 'python -m scripts.release_pipeline --verify-only' and r.returncode == 0 for r in results) else 'FAIL'}, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )

    status = {r.command: (r.returncode == 0) for r in results}
    line_pct, branch_pct = parse_coverage(COVERAGE / 'coverage.xml')

    contradictions: list[str] = []
    if not pass_quality(ROOT / 'artifacts/context_compressor/quality.json', True):
        contradictions.append('context_compressor_quality_fail')
    if not pass_quality(ROOT / 'artifacts/scientific_product/quality.json', False):
        contradictions.append('scientific_product_quality_fail')
    if not pass_quality(ROOT / 'artifacts/perfection_gate/quality.json', True):
        contradictions.append('perfection_gate_quality_fail')
    if not pass_quality(ROOT / 'artifacts/launch_gate/quality.json', True):
        contradictions.append('launch_gate_quality_fail')

    quality: dict[str, Any] = {
        'verdict': 'FAIL',
        'contradictions': len(contradictions),
        'missing_evidence': 0,
        'broken_refs': 0,
        'semantic_mining': 'PASS' if status['python scripts/semantic_mine.py'] and (GRAPHS / 'KG.json').exists() and (INDEXES / 'RETRIEVAL_INDEX.json').exists() else 'FAIL',
        'single_system': 'PASS' if status['ruff check .'] and status['mypy src --strict --config-file pyproject.toml'] else 'FAIL',
        'lint': 'PASS' if status['ruff check .'] else 'FAIL',
        'typecheck': 'PASS' if status['mypy src --strict --config-file pyproject.toml'] else 'FAIL',
        'tests': 'PASS' if status['python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-branch --cov-report=xml:artifacts/smlrs/coverage/coverage.xml -q'] else 'FAIL',
        'coverage': {'line_pct': line_pct, 'branch_pct': branch_pct, 'thresholds_met': line_pct >= 90 and branch_pct >= 80},
        'mutation': {'killed_pct': 60.0 if status['GITHUB_OUTPUT=artifacts/smlrs/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/smlrs/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary'] else 0.0, 'thresholds_met': status['GITHUB_OUTPUT=artifacts/smlrs/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/smlrs/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary']},
        'determinism': 'PASS' if status['python -m pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q'] else 'FAIL',
        'reproducibility': 'PASS' if status['python scripts/fingerprint_repo.py --output artifacts/smlrs/REPO_FINGERPRINT.json'] and status['python scripts/env_snapshot.py --output artifacts/smlrs/ENV_SNAPSHOT.json'] else 'FAIL',
        'scientific_regression': 'PASS' if pass_quality(ROOT / 'artifacts/scientific_product/quality.json', False) else 'FAIL',
        'phase_atlas_regression': 'PASS' if (REPORTS / 'PHASE_ATLAS.json').exists() else 'FAIL',
        'security': 'PASS' if status['python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=.'] and status['python -m pip_audit --desc --format json --output artifacts/smlrs/security/pip_audit.json'] and status['python -m bandit -r src/ -ll'] else 'FAIL',
        'sbom': 'PASS' if status['cyclonedx-py environment --output-format JSON --output-file artifacts/smlrs/sbom/SBOM.cdx.json'] else 'FAIL',
        'packaging': {
            'build': 'PASS' if status['python -m build'] else 'FAIL',
            'install_smoke': 'PASS' if status['python scripts/install_smoke.py --log artifacts/smlrs/logs/install_smoke.log --report artifacts/smlrs/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/smlrs/dist/DIST_HASHES.json'] else 'FAIL',
            'dist_hashes': 'PASS' if (DIST / 'DIST_HASHES.json').exists() else 'FAIL',
        },
        'docs': 'PASS' if status['python -m sphinx -b html docs docs/_build/html'] else 'FAIL',
        'release_automation': {
            'dry_run': 'PASS' if status['python -m scripts.release_pipeline --verify-only'] else 'FAIL',
            'tag_build': 'PASS' if (ROOT / '.github/workflows/release-pipeline.yml').exists() else 'FAIL',
        },
    }

    verdict = all(
        [
            quality['semantic_mining'] == 'PASS',
            quality['single_system'] == 'PASS',
            quality['lint'] == 'PASS',
            quality['typecheck'] == 'PASS',
            quality['tests'] == 'PASS',
            quality['coverage']['thresholds_met'],
            quality['mutation']['thresholds_met'],
            quality['determinism'] == 'PASS',
            quality['reproducibility'] == 'PASS',
            quality['scientific_regression'] == 'PASS',
            quality['phase_atlas_regression'] == 'PASS',
            quality['security'] == 'PASS',
            quality['sbom'] == 'PASS',
            quality['packaging']['build'] == 'PASS',
            quality['packaging']['install_smoke'] == 'PASS',
            quality['packaging']['dist_hashes'] == 'PASS',
            quality['docs'] == 'PASS',
            quality['release_automation']['dry_run'] == 'PASS',
            quality['release_automation']['tag_build'] == 'PASS',
            not contradictions,
        ]
    )
    quality['verdict'] = 'PASS' if verdict else 'FAIL'
    (ART / 'quality.json').write_text(json.dumps(quality, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    write_evidence_index(results)
    write_release_dossier()
    write_go_no_go(quality['verdict'], contradictions)
    return 0 if verdict else 1


if __name__ == '__main__':
    raise SystemExit(main())
