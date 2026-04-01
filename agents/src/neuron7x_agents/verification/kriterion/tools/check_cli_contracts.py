#!/usr/bin/env python3
"""CLI contract checks for governance-critical tools."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

TOOL_CONTRACTS = [
    ("tools/validate_json.py", "help"),
    ("tools/verify_manifest.py", "help"),
    ("tools/canonicalize_and_hash.py", "help"),
    ("tools/reference_runner.py", "help"),
    ("tools/verify_execution_chain.py", "help"),
    ("tools/validate_governance.py", "help"),
    ("tools/render_governance_checklist.py", "run"),
    ("tools/check_internal_links.py", "help"),
    ("tools/check_external_links.py", "help"),
    ("tools/validate_publication_surfaces.py", "help"),
    ("tools/verify_ci_artifact_manifest.py", "help"),
    ("tools/assert_fail_closed_semantics.py", "help"),
    ("tools/assert_gate_benchmark_invariants.py", "help"),
    ("tools/assert_worked_example_semantics.py", "help"),
    ("tools/check_canonical_hash_stability.py", "help"),
    ("tools/check_canonicalization_negative_cases.py", "run"),
    ("tools/check_dependency_hermeticity.py", "run"),
    ("tools/check_governance_nondeterminism.py", "run"),
    ("tools/run_local_governance_baseline.py", "help"),
    ("tools/validate_pr_intake.py", "help"),
    ("tools/compile_pr_intake.py", "help"),
]


def _tool_env(tool: str) -> dict[str, str] | None:
    if tool != "tools/validate_pr_intake.py":
        return None
    env = dict(__import__("os").environ)
    env.pop("GITHUB_EVENT_NAME", None)
    env.pop("GITHUB_EVENT_PATH", None)
    return env


def must_help(tool: str) -> None:
    proc = subprocess.run(["python", tool, "-h"], check=False, capture_output=True, text=True, env=_tool_env(tool))
    assert proc.returncode == 0, (tool, proc.stdout, proc.stderr)
    out = (proc.stdout + proc.stderr).lower()
    assert "usage" in out or "help" in out or "pr_intake_check_skipped" in out, (tool, out[:500])


def must_run(tool: str) -> None:
    proc = subprocess.run(["python", tool], check=False, capture_output=True, text=True, env=_tool_env(tool))
    assert proc.returncode == 0, (tool, proc.stdout, proc.stderr)


def main() -> int:
    for tool, mode in TOOL_CONTRACTS:
        if mode == "help":
            must_help(tool)
        else:
            must_run(tool)

    proc = subprocess.run(["python", "tools/validate_governance.py", "--json"], check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    start = proc.stdout.find("{")
    end = proc.stdout.rfind("}")
    payload = json.loads(proc.stdout[start : end + 1])
    assert payload["status"] in {"OK", "FAILED"}
    assert "policy_version" in payload
    assert isinstance(payload.get("violations"), list)

    with tempfile.TemporaryDirectory(prefix="cli-contracts-") as tmp:
        result_path = Path(tmp) / "result.json"
        run = subprocess.run(
            [
                "python",
                "tools/reference_runner.py",
                "examples/worked-example/SE_WORKED_EXAMPLE_INPUT.json",
                "--allow-non-authoritative-git",
                "--output",
                str(result_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert run.returncode == 0, run.stdout + run.stderr
        verify = subprocess.run(
            [
                "python",
                "tools/verify_execution_chain.py",
                "--input",
                "examples/worked-example/SE_WORKED_EXAMPLE_INPUT.json",
                "--result",
                str(result_path),
                "--allow-non-authoritative-git",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert verify.returncode == 0, verify.stdout + verify.stderr
        verify_payload = json.loads(verify.stdout)
        assert verify_payload["status"] == "VERIFIED"
        assert verify_payload["chain_format_version"] == "execution_chain.v1"
        assert "result_terminal_hash" in verify_payload
        assert "input_bundle_hash" in verify_payload
        assert "verified_at" in verify_payload


    with tempfile.TemporaryDirectory(prefix="pcos-cli-contracts-") as tmp:
        tmpdir = Path(tmp)
        ir = tmpdir / "pcos.ir.json"
        manifest = tmpdir / "pcos.manifest.json"
        prompt = Path("examples/pure_symbolic.prompt")
        assert subprocess.run(["python", "-m", "pcos.cli", "compile", str(prompt), "--out", str(ir)], check=False).returncode == 0
        assert subprocess.run(["python", "-m", "pcos.cli", "run", str(ir), "--out", str(manifest)], check=False).returncode == 0
        assert subprocess.run(["python", "-m", "pcos.cli", "verify", str(manifest)], check=False).returncode == 0
        assert subprocess.run(["python", "-m", "pcos.cli", "replay", str(manifest)], check=False).returncode == 0
        bench = subprocess.run(["python", "-m", "pcos.cli", "bench"], check=False, capture_output=True, text=True)
        assert bench.returncode == 0, bench.stdout + bench.stderr
        bench_payload = json.loads(bench.stdout)
        assert bench_payload["status"] == "PASS"
        assert bench_payload["passed"] == bench_payload["cases"]

    print("CLI_CONTRACTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
