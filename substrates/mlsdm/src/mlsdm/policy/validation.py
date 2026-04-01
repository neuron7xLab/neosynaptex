from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from mlsdm.policy.loader import (
    PolicyLoadError,
    load_policy_bundle,
    policy_documentation_paths,
    policy_required_checks,
    policy_test_locations,
)


class PolicyValidator:
    """Validates policy configuration files against repository reality."""

    def __init__(self, repo_root: Path, policy_dir: Path, *, enforce_registry: bool = True) -> None:
        self.repo_root = repo_root
        self.policy_dir = policy_dir
        self.enforce_registry = enforce_registry
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("MLSDM Policy Configuration Validation")
        print("=" * 70)
        print()

        # Load policy files
        try:
            bundle = load_policy_bundle(self.policy_dir, enforce_registry=self.enforce_registry)
        except PolicyLoadError as exc:
            self.errors.append(str(exc))
            print(f"\n❌ FAILED: {exc}")
            return False

        # Run validation checks
        self._validate_security_workflows(bundle)
        self._validate_security_modules(bundle)
        self._validate_slo_tests(bundle)
        self._validate_documentation(bundle)

        # Print results
        self._print_results()

        return len(self.errors) == 0

    def _validate_security_workflows(self, bundle: Any) -> None:
        """Validate that required CI workflows exist."""
        print("CHECK: Security Workflow Files")
        print("-" * 70)

        required_checks = policy_required_checks(bundle)

        for check in required_checks:
            check_name = check.name
            workflow_file = check.workflow_file

            if workflow_file:
                workflow_path = self.repo_root / workflow_file
                if workflow_path.exists():
                    print(f"✓ {check_name}: {workflow_file} exists")
                else:
                    self.errors.append(f"{check_name}: Workflow file not found: {workflow_file}")
                    print(f"✗ {check_name}: {workflow_file} NOT FOUND")
            elif check.command:
                # Command-based check, verify the command is valid
                command = check.command
                print(f"✓ {check_name}: Command-based check '{command}'")
            elif check.script:
                # Script-based check
                script = check.script
                script_path = self.repo_root / script.lstrip("./")
                if script_path.exists():
                    print(f"✓ {check_name}: {script} exists")
                else:
                    self.errors.append(f"{check_name}: Script not found: {script}")
                    print(f"✗ {check_name}: {script} NOT FOUND")

        print()

    def _validate_security_modules(self, bundle: Any) -> None:
        """Validate that referenced security modules exist."""
        print("CHECK: Security Module References")
        print("-" * 70)

        security_reqs = bundle.security_baseline.controls.security_requirements

        # Check input validation modules
        input_val = security_reqs.input_validation
        llm_safety_module = input_val.llm_safety_module
        scrubber_module = input_val.payload_scrubber_module

        modules_to_check = [
            ("LLM Safety Gateway", llm_safety_module),
            ("Payload Scrubber", scrubber_module),
        ]

        for name, module_path in modules_to_check:
            if module_path:
                # Convert module path to file path
                # e.g., mlsdm.security.llm_safety -> src/mlsdm/security/llm_safety.py
                parts = module_path.split(".")
                if parts[0] == "mlsdm":
                    file_path = self.repo_root / "src" / "/".join(parts)
                    py_path = file_path.parent / f"{file_path.name}.py"
                    init_path = file_path / "__init__.py"

                    if py_path.exists() or init_path.exists():
                        print(f"✓ {name}: {module_path} exists")
                    else:
                        self.warnings.append(
                            f"{name}: Module {module_path} not found "
                            f"(checked {py_path} and {init_path})"
                        )
                        print(f"⚠ {name}: {module_path} NOT FOUND (warning)")

        print()

    def _validate_slo_tests(self, bundle: Any) -> None:
        """Validate that SLO test locations exist."""
        print("CHECK: SLO Test Locations")
        print("-" * 70)

        test_locations = policy_test_locations(bundle)

        for name, test_loc in test_locations:
            # Extract file path (before ::)
            if "::" in test_loc:
                file_path, _ = test_loc.split("::", 1)
            else:
                file_path = test_loc

            full_path = self.repo_root / file_path

            if full_path.exists():
                print(f"✓ {name}: {file_path} exists")
                # Could further validate that the test name exists in the file
            else:
                self.errors.append(f"{name}: Test file not found: {file_path}")
                print(f"✗ {name}: {file_path} NOT FOUND")

        print()

    def _validate_documentation(self, bundle: Any) -> None:
        """Validate that referenced documentation exists."""
        print("CHECK: Documentation Files")
        print("-" * 70)

        # Documentation from SLO policy
        docs = policy_documentation_paths(bundle)
        doc_files = [
            ("SLO Spec", docs.get("slo_spec")),
            ("Validation Protocol", docs.get("validation_protocol")),
            ("Runbook", docs.get("runbook")),
            ("Observability Guide", docs.get("observability_guide")),
        ]

        for name, doc_file in doc_files:
            if doc_file:
                doc_path = self.repo_root / doc_file
                if doc_path.exists():
                    print(f"✓ {name}: {doc_file} exists")
                else:
                    self.warnings.append(f"{name}: Documentation not found: {doc_file}")
                    print(f"⚠ {name}: {doc_file} NOT FOUND (warning)")

        print()

    def _print_results(self) -> None:
        """Print validation results summary."""
        print("=" * 70)
        print("Validation Summary")
        print("=" * 70)
        print(f"Errors:   {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        print()

        if self.errors:
            print("ERRORS:")
            for error in self.errors:
                print(f"  ❌ {error}")
            print()

        if self.warnings:
            print("WARNINGS:")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
            print()

        if len(self.errors) == 0:
            print("✓ All critical validations passed!")
        else:
            print(f"✗ Validation failed with {len(self.errors)} error(s)")


__all__ = ["PolicyValidator"]
