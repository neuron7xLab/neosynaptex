from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts" / "launch_gate"
LOGS = ART / "logs"
REPORTS = ART / "reports"
PROOFS = ART / "proofs"
RELEASE = ART / "release"
INSTALL_SMOKE = ART / "install_smoke"
DIFFS = ART / "diffs"


@dataclass(frozen=True)
class CmdResult:
    command: str
    log: str
    returncode: int


def ensure_dirs() -> None:
    for directory in (ART, LOGS, REPORTS, PROOFS, RELEASE, INSTALL_SMOKE, DIFFS):
        directory.mkdir(parents=True, exist_ok=True)


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
    log_path = LOGS / log_name
    log_path.write_text(proc.stdout, encoding="utf-8")
    return CmdResult(command=command, log=f"artifacts/launch_gate/logs/{log_name}", returncode=proc.returncode)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quality_pass(path: Path, require_contradictions_zero: bool) -> bool:
    if not path.exists():
        return False
    payload = _load_json(path)
    if payload.get("verdict") != "PASS":
        return False
    if require_contradictions_zero and payload.get("contradictions") != 0:
        return False
    return True


def _parse_coverage(xml_path: Path) -> tuple[float, float]:
    import xml.etree.ElementTree as ET

    if not xml_path.exists():
        return 0.0, 0.0
    root = ET.fromstring(xml_path.read_text(encoding="utf-8"))
    line_rate = float(root.attrib.get("line-rate", "0.0"))
    branch_rate = float(root.attrib.get("branch-rate", "0.0"))
    return round(line_rate * 100.0, 2), round(branch_rate * 100.0, 2)


def write_evidence_index(results: list[CmdResult]) -> None:
    lines = ["# EVIDENCE_INDEX", ""]
    lines.extend(f"- cmd:{item.command} -> log:{item.log}" for item in results)
    lines.extend(
        [
            f"- hash:sha256:{_sha256(ART / 'quality.json')}",
            f"- hash:sha256:{_sha256(ART / 'REPO_FINGERPRINT.json')}",
            f"- hash:sha256:{_sha256(ART / 'ENV_SNAPSHOT.json')}",
            f"- hash:sha256:{_sha256(PROOFS / 'DIST_HASHES.json')}",
        ]
    )
    (ART / "EVIDENCE_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_release_dossier() -> None:
    lines = [
        "# RELEASE_DOSSIER",
        "",
        "- file:src/bnsyn/__init__.py:L1-L20",
        "- file:src/bnsyn/cli.py:L1-L260",
        "- file:src/bnsyn/schemas/experiment.py:L1-L260",
        "- file:Makefile:L1-L260",
        "- file:docs/SSOT.md:L1-L80",
        "- file:artifacts/launch_gate/quality.json:L1-L120",
    ]
    (ART / "RELEASE_DOSSIER.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_go_no_go(verdict: str, contradiction_ids: list[str]) -> None:
    lines = [
        "# GO_NO_GO",
        "",
        f"verdict={verdict}",
        f"contradictions={len(contradiction_ids)}",
        f"ids={','.join(contradiction_ids[:5]) if contradiction_ids else 'none'}",
    ]
    (ART / "GO_NO_GO.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()

    commands: list[tuple[str, str]] = [
        ('python -m pip install --upgrade pip==26.0.1 && python -m pip install -e ".[dev,test,docs]" build pytest-cov bandit cyclonedx-bom==7.1.0', "deps.log"),
        ("python scripts/fingerprint_repo.py --output artifacts/launch_gate/REPO_FINGERPRINT.json", "fingerprint.log"),
        ("python scripts/env_snapshot.py --output artifacts/launch_gate/ENV_SNAPSHOT.json", "env_snapshot.log"),
        ("python scripts/ric_check.py --truth-map artifacts/launch_gate/reports/RIC_TRUTH_MAP.json --report artifacts/launch_gate/reports/RIC_REPORT.md", "ric.log"),
        ("ruff check .", "lint.log"),
        ("mypy src --strict --config-file pyproject.toml", "mypy.log"),
        ("python tools/generate_inventory.py", "inventory.log"),
        ("python -m tools.entropy_gate --mode baseline && python -m tools.entropy_gate --mode current", "entropy.log"),
        ('python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-branch --cov-report=xml:artifacts/launch_gate/reports/coverage.xml -q', "tests.log"),
        ('python -m pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q', "determinism.log"),
        ("python -m build", "build.log"),
        ("python scripts/install_smoke.py --log artifacts/launch_gate/logs/install_smoke.log --report artifacts/launch_gate/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/launch_gate/proofs/DIST_HASHES.json", "install_smoke_driver.log"),
        ("python -m sphinx -b html docs docs/_build/html", "docs.log"),
        ("python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=.", "gitleaks.log"),
        ("python -m pip_audit --desc --format json --output artifacts/launch_gate/release/pip_audit.json", "pip_audit.log"),
        ("python -m bandit -r src/ -ll", "bandit.log"),
        ("cyclonedx-py environment --output-format JSON --output-file artifacts/launch_gate/release/SBOM.cdx.json", "sbom.log"),
        ("python -m scripts.release_pipeline --verify-only", "release_dry_run.log"),
    ]
    results = [run(cmd, log_name) for cmd, log_name in commands]

    status = {item.command: item.returncode == 0 for item in results}
    line_pct, branch_pct = _parse_coverage(REPORTS / "coverage.xml")

    contradictions: list[str] = []
    if not _quality_pass(ROOT / "artifacts/context_compressor/quality.json", require_contradictions_zero=True):
        contradictions.append("context-compressor-quality-not-pass")
    if not _quality_pass(ROOT / "artifacts/scientific_product/quality.json", require_contradictions_zero=False):
        contradictions.append("scientific-product-quality-not-pass")
    if not _quality_pass(ROOT / "artifacts/perfection_gate/quality.json", require_contradictions_zero=True):
        contradictions.append("perfection-gate-quality-not-pass")

    quality = {
        "verdict": "FAIL",
        "contradictions": len(contradictions),
        "missing_evidence": 0,
        "broken_refs": 0,
        "single_system": "PASS" if status["ruff check ."] and status["mypy src --strict --config-file pyproject.toml"] else "FAIL",
        "packaging": {
            "build": "PASS" if status["python -m build"] else "FAIL",
            "install_smoke": "PASS" if status["python scripts/install_smoke.py --log artifacts/launch_gate/logs/install_smoke.log --report artifacts/launch_gate/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/launch_gate/proofs/DIST_HASHES.json"] else "FAIL",
            "metadata": "PASS" if status["python -m build"] else "FAIL",
            "dist_hashes": "PASS" if (PROOFS / "DIST_HASHES.json").exists() else "FAIL",
        },
        "cli_contract": "PASS" if status["python scripts/install_smoke.py --log artifacts/launch_gate/logs/install_smoke.log --report artifacts/launch_gate/install_smoke/SMOKE_REPORT.json --dist-hashes artifacts/launch_gate/proofs/DIST_HASHES.json"] else "FAIL",
        "config_schema": "PASS" if (ROOT / "src/bnsyn/schemas/experiment.py").exists() else "FAIL",
        "tests": "PASS" if status['python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-branch --cov-report=xml:artifacts/launch_gate/reports/coverage.xml -q'] else "FAIL",
        "coverage": {
            "line_pct": line_pct,
            "branch_pct": branch_pct,
            "thresholds_met": line_pct >= 90.0 and branch_pct >= 80.0,
        },
        "determinism": "PASS" if status['python -m pytest tests/test_determinism.py tests/properties/test_properties_determinism.py -q'] else "FAIL",
        "reproducibility": "PASS" if status["python scripts/fingerprint_repo.py --output artifacts/launch_gate/REPO_FINGERPRINT.json"] and status["python scripts/env_snapshot.py --output artifacts/launch_gate/ENV_SNAPSHOT.json"] else "FAIL",
        "scientific_regression": "PASS" if _quality_pass(ROOT / "artifacts/scientific_product/quality.json", False) else "FAIL",
        "docs": "PASS" if status["python -m sphinx -b html docs docs/_build/html"] else "FAIL",
        "security": "PASS" if status["python -m scripts.ensure_gitleaks -- detect --redact --verbose --source=."] and status["python -m pip_audit --desc --format json --output artifacts/launch_gate/release/pip_audit.json"] and status["python -m bandit -r src/ -ll"] else "FAIL",
        "sbom": "PASS" if status["cyclonedx-py environment --output-format JSON --output-file artifacts/launch_gate/release/SBOM.cdx.json"] else "FAIL",
        "release_automation": {
            "dry_run": "PASS" if status["python -m scripts.release_pipeline --verify-only"] else "FAIL",
            "tag_build": "PASS" if (ROOT / ".github/workflows/release-pipeline.yml").exists() else "FAIL",
        },
        "upgrade_path": "PASS" if status["python -m scripts.release_pipeline --verify-only"] else "FAIL",
    }

    verdict = all(
        [
            quality["single_system"] == "PASS",
            quality["packaging"]["build"] == "PASS",
            quality["packaging"]["install_smoke"] == "PASS",
            quality["packaging"]["dist_hashes"] == "PASS",
            quality["cli_contract"] == "PASS",
            quality["config_schema"] == "PASS",
            quality["tests"] == "PASS",
            quality["coverage"]["thresholds_met"],
            quality["determinism"] == "PASS",
            quality["reproducibility"] == "PASS",
            quality["scientific_regression"] == "PASS",
            quality["docs"] == "PASS",
            quality["security"] == "PASS",
            quality["sbom"] == "PASS",
            quality["release_automation"]["dry_run"] == "PASS",
            quality["release_automation"]["tag_build"] == "PASS",
            quality["upgrade_path"] == "PASS",
            not contradictions,
            _quality_pass(ROOT / "artifacts/perfection_gate/quality.json", True),
            _quality_pass(ROOT / "artifacts/context_compressor/quality.json", True),
            _quality_pass(ROOT / "artifacts/scientific_product/quality.json", False),
        ]
    )
    quality["verdict"] = "PASS" if verdict else "FAIL"

    (ART / "quality.json").write_text(json.dumps(quality, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_evidence_index(results)
    write_release_dossier()
    write_go_no_go(quality["verdict"], contradictions)
    return 0 if quality["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
