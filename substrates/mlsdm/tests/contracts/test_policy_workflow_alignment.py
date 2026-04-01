"""
Test suite to validate policy-workflow-script alignment.

This test ensures that policy files, CI workflows, and scripts remain synchronized
to prevent truth-alignment drift.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from mlsdm.policy.loader import SecurityBaselinePolicy, load_policy_bundle


@pytest.mark.skipif(not YAML_AVAILABLE, reason="PyYAML not installed")
class TestPolicyWorkflowAlignment:
    """Test that policy files match workflow and script reality."""

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get repository root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def security_policy(self) -> SecurityBaselinePolicy:
        """Load security baseline policy."""
        return load_policy_bundle().security_baseline

    def test_policy_required_checks_exist(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify all required checks reference existing files/commands."""
        required_checks = security_policy.controls.required_checks
        assert len(required_checks) > 0, "Policy must define required checks"

        for check in required_checks:
            check_name = check.name

            # Check workflow file exists if specified
            if check.workflow_file:
                workflow_file = repo_root / check.workflow_file
                assert workflow_file.exists(), (
                    f"{check_name}: Workflow file not found: {check.workflow_file}"
                )

            # Check script exists if specified
            if check.script:
                script_path = repo_root / check.script.lstrip("./")
                assert script_path.exists(), (
                    f"{check_name}: Script not found: {check.script}"
                )

    def test_coverage_threshold_consistency(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify coverage threshold is consistent between policy and coverage_gate.sh."""
        # Get policy coverage threshold
        policy_threshold = security_policy.thresholds.coverage_gate_minimum_percent

        # Parse coverage_gate.sh for default threshold
        coverage_script = repo_root / "coverage_gate.sh"
        assert coverage_script.exists(), "coverage_gate.sh not found"

        with open(coverage_script, encoding="utf-8") as f:
            content = f.read()

        # Look for COVERAGE_MIN default value
        # Format: COVERAGE_MIN="${COVERAGE_MIN:-65}"
        match = re.search(r'COVERAGE_MIN="\$\{COVERAGE_MIN:-(\d+)\}"', content)
        assert match is not None, "COVERAGE_MIN default not found in coverage_gate.sh"

        script_threshold = int(match.group(1))

        # Both should be in percentage (not ratio)
        # Policy should match script default
        assert policy_threshold == script_threshold, (
            f"Coverage threshold mismatch: "
            f"policy={policy_threshold}%, script default={script_threshold}%"
        )

    def test_security_modules_exist(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify referenced security modules exist in codebase."""
        security_reqs = security_policy.controls.security_requirements

        # Check input validation modules
        input_val = security_reqs.input_validation
        modules_to_check = [
            input_val.llm_safety_module,
            input_val.payload_scrubber_module,
        ]

        for module_path in modules_to_check:
            if not module_path:
                continue

            # Convert module path to file path
            # e.g., mlsdm.security.llm_safety -> src/mlsdm/security/llm_safety.py
            parts = module_path.split(".")
            if parts[0] == "mlsdm":
                file_path = repo_root / "src" / Path(*parts)
                py_path = file_path.parent / f"{file_path.name}.py"
                init_path = file_path / "__init__.py"

                assert py_path.exists() or init_path.exists(), (
                    f"Module not found: {module_path} "
                    f"(checked {py_path} and {init_path})"
                )

    def test_scrubber_implementation_exists(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify payload scrubber implementation exists."""
        security_reqs = security_policy.controls.security_requirements
        data_protection = security_reqs.data_protection

        scrubber_module = data_protection.scrubber_implementation
        assert scrubber_module is not None, "scrubber_implementation not specified"

        # Convert to file path
        parts = scrubber_module.split(".")
        if parts[0] == "mlsdm":
            file_path = repo_root / "src" / Path(*parts)
            py_path = file_path.parent / f"{file_path.name}.py"
            init_path = file_path / "__init__.py"

            assert py_path.exists() or init_path.exists(), (
                f"Scrubber implementation not found: {scrubber_module}"
            )

    def test_policy_validator_script_passes(self, repo_root: Path) -> None:
        """Verify the policy validator script passes."""
        validator_script = repo_root / "scripts" / "validate_policy_config.py"
        assert validator_script.exists(), "validate_policy_config.py not found"

        # Run the validator
        result = subprocess.run(
            ["python", str(validator_script)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should pass (exit 0) and report success
        assert result.returncode == 0, (
            f"Policy validation failed:\n{result.stdout}\n{result.stderr}"
        )
        assert "All critical validations passed" in result.stdout, (
            "Policy validation did not report success"
        )

    def test_sast_workflows_exist(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify SAST scan workflows exist and are configured correctly."""
        required_checks = security_policy.controls.required_checks

        # Find SAST-related checks
        sast_checks = [
            check for check in required_checks
            if check.name in ["bandit", "semgrep", "codeql"]
        ]

        assert len(sast_checks) > 0, "No SAST checks found in policy"

        for check in sast_checks:
            workflow_file = check.workflow_file
            if workflow_file:
                workflow_path = repo_root / workflow_file
                assert workflow_path.exists(), (
                    f"{check.name}: Workflow file not found: {workflow_file}"
                )

                # Read workflow and verify job exists
                with open(workflow_path, encoding="utf-8") as f:
                    workflow_content = yaml.safe_load(f)

                jobs = workflow_content.get("jobs", {})
                check_name = check.name

                # Verify job name exists in workflow (case-insensitive match)
                job_names = [name.lower() for name in jobs]
                assert check_name.lower() in job_names, (
                    f"{check_name}: Job not found in {workflow_file}"
                )

    def test_dependency_audit_workflow_exists(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify dependency audit workflow exists and is properly configured."""
        required_checks = security_policy.controls.required_checks

        # Find dependency-audit check
        dep_audit_check = next(
            (c for c in required_checks if c.name == "dependency-audit"),
            None
        )
        assert dep_audit_check is not None, "dependency-audit check not found in policy"

        workflow_file = dep_audit_check.workflow_file
        assert workflow_file is not None, "dependency-audit check missing workflow_file"

        workflow_path = repo_root / workflow_file
        assert workflow_path.exists(), f"Workflow file not found: {workflow_file}"

        # Verify job exists in workflow
        with open(workflow_path, encoding="utf-8") as f:
            workflow_content = yaml.safe_load(f)

        jobs = workflow_content.get("jobs", {})
        assert "dependency-audit" in jobs, "dependency-audit job not found in workflow"

    def test_secrets_scan_workflow_exists(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify secrets scanning workflow exists and is properly configured."""
        required_checks = security_policy.controls.required_checks

        # Find secrets-scan check
        secrets_check = next(
            (c for c in required_checks if c.name == "secrets-scan"),
            None
        )
        assert secrets_check is not None, "secrets-scan check not found in policy"

        workflow_file = secrets_check.workflow_file
        assert workflow_file is not None, "secrets-scan check missing workflow_file"

        workflow_path = repo_root / workflow_file
        assert workflow_path.exists(), f"Workflow file not found: {workflow_file}"

        # Verify job exists in workflow
        with open(workflow_path, encoding="utf-8") as f:
            workflow_content = yaml.safe_load(f)

        jobs = workflow_content.get("jobs", {})
        assert "secrets-scan" in jobs, "secrets-scan job not found in workflow"

    def test_workflow_permissions_are_least_privilege(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify CI workflows use least-privilege permissions (no write-all)."""
        def canon_permissions(value: object) -> tuple[str, object]:
            if isinstance(value, str):
                return ("str", value)
            if isinstance(value, dict):
                return ("dict", tuple(sorted((key, str(val)) for key, val in value.items())))
            if value is None:
                return ("none", "")
            return ("other", repr(value))

        workflows_dir = repo_root / ".github" / "workflows"
        assert workflows_dir.exists(), "Workflows directory not found"
        prohibited_raw = security_policy.controls.ci_workflow_policy.prohibited_permissions
        prohibited = {canon_permissions(permission) for permission in prohibited_raw}

        # Check all workflow files
        for workflow_file in workflows_dir.glob("*.yml"):
            with open(workflow_file, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if content is None:
                continue

            # Check top-level permissions
            top_permissions = content.get("permissions")
            assert canon_permissions(top_permissions) not in prohibited, (
                f"{workflow_file.name}: Workflow has prohibited permissions (security risk)"
            )

            # Check job-level permissions
            jobs = content.get("jobs", {})
            for job_name, job_config in jobs.items():
                if not isinstance(job_config, dict):
                    continue

                job_permissions = job_config.get("permissions")
                assert canon_permissions(job_permissions) not in prohibited, (
                    f"{workflow_file.name}: Job '{job_name}' has prohibited permissions (security risk)"
                )

    def test_third_party_actions_in_sast_are_pinned(
        self, repo_root: Path, security_policy: SecurityBaselinePolicy
    ) -> None:
        """Verify third-party actions in sast-scan.yml are pinned to SHA."""
        sast_workflow = repo_root / ".github" / "workflows" / "sast-scan.yml"
        assert sast_workflow.exists(), "sast-scan.yml not found"

        with open(sast_workflow, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        jobs = content.get("jobs", {})
        # Support both SHA-1 (40 chars) and SHA-256 (64 chars) commit hashes
        sha_pattern = re.compile(r"@[a-f0-9]{40,64}$")

        third_party_actions = []
        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue

            steps = job_config.get("steps", [])
            for step in steps:
                uses = step.get("uses", "")
                if not uses:
                    continue

                third_party_actions.append((job_name, uses))

        first_party = tuple(security_policy.controls.ci_workflow_policy.first_party_action_owners)

        # Verify each third-party action is pinned to SHA
        for job_name, action in third_party_actions:
            owner = action.split("/", 1)[0]
            if owner in first_party:
                continue

            assert sha_pattern.search(action), (
                f"Job '{job_name}': Third-party action '{action}' should be pinned to SHA "
                "for supply-chain security"
            )

    def test_coverage_timeout_adequate_safety_margin(self, repo_root: Path) -> None:
        """
        Verify coverage timeout has sufficient buffer vs historical evidence.
        
        Security invariant: timeout must prevent workflow-level timeout (20min)
        while allowing 135% of historical maximum execution time.
        
        Historical evidence (2026-01-24):
        - 1020s reached 92% completion
        - Extrapolated full run: 1109s
        - Required safety margin: 35% (accounts for runner variance + future growth)
        """
        workflow_path = repo_root / ".github/workflows/coverage-badge.yml"
        assert workflow_path.exists(), "coverage-badge.yml workflow not found"
        
        content = workflow_path.read_text(encoding="utf-8")
        
        # Extract COVERAGE_SOFT_LIMIT_SECONDS
        match = re.search(
            r'COVERAGE_SOFT_LIMIT_SECONDS:\s*["\']?(\d+)["\']?',
            content
        )
        assert match is not None, \
            "COVERAGE_SOFT_LIMIT_SECONDS not found in workflow"
        
        timeout_seconds = int(match.group(1))
        
        # Historical evidence-based thresholds
        HISTORICAL_MAX_EXECUTION = 1109  # seconds (extrapolated from 92% @ 1020s)
        SAFETY_MARGIN = 1.35  # 35% buffer
        MIN_SAFE_TIMEOUT = int(HISTORICAL_MAX_EXECUTION * SAFETY_MARGIN)  # 1497s
        
        # Workflow-level constraint (job timeout in coverage-badge.yml: 30min)
        WORKFLOW_TIMEOUT = 1800  # 30 minutes in seconds
        MAX_SAFE_TIMEOUT = WORKFLOW_TIMEOUT - 60  # Leave 60s for cleanup
        
        assert timeout_seconds >= MIN_SAFE_TIMEOUT, \
            f"Coverage timeout {timeout_seconds}s below safe minimum {MIN_SAFE_TIMEOUT}s " \
            f"(historical max: {HISTORICAL_MAX_EXECUTION}s × {SAFETY_MARGIN} margin)"
        
        assert timeout_seconds <= MAX_SAFE_TIMEOUT, \
            f"Coverage timeout {timeout_seconds}s exceeds workflow limit " \
            f"(max: {MAX_SAFE_TIMEOUT}s for 30min workflow)"
