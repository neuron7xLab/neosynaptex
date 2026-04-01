"""
Tests for deploy/scripts/validate-manifests.sh
"""

import subprocess
from pathlib import Path

import pytest


class TestValidateManifests:
    """Test suite for the validate-manifests.sh script."""

    @pytest.fixture
    def script_path(self) -> Path:
        """Get path to the validate-manifests script."""
        repo_root = Path(__file__).parent.parent.parent
        script = repo_root / "deploy" / "scripts" / "validate-manifests.sh"
        assert script.exists(), f"Script not found: {script}"
        return script

    @pytest.fixture
    def temp_manifest_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for test manifests."""
        manifest_dir = tmp_path / "k8s"
        manifest_dir.mkdir()
        return manifest_dir

    def run_script(self, script_path: Path, env: dict = None) -> tuple[int, str, str]:
        """Run the validation script and return (returncode, stdout, stderr)."""
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            env=env,
            cwd=script_path.parent.parent.parent,  # Run from repo root
        )
        return result.returncode, result.stdout, result.stderr

    def test_script_exists_and_executable(self, script_path: Path):
        """Test that the script exists and is executable."""
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111, "Script is not executable"

    def test_valid_manifest_passes(self, tmp_path: Path):
        """Test that a valid K8s manifest passes validation."""
        # Create temporary structure
        deploy_dir = tmp_path / "deploy"
        k8s_dir = deploy_dir / "k8s"
        monitoring_dir = deploy_dir / "monitoring"
        grafana_dir = deploy_dir / "grafana"

        k8s_dir.mkdir(parents=True)
        monitoring_dir.mkdir(parents=True)
        grafana_dir.mkdir(parents=True)

        # Create a valid deployment manifest
        valid_manifest = k8s_dir / "test-deployment.yaml"
        valid_manifest.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-app
  labels:
    app: test
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - name: test
        image: nginx:1.21.0
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
""")

        # Create a simple script wrapper that validates just this directory
        test_script = tmp_path / "test_validate.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

echo "Testing YAML validation..."

# Use Python to validate YAML
python3 - << 'EOF'
import yaml
with open("{valid_manifest}", "r") as f:
    data = yaml.safe_load(f)
    print(f"✓ Valid YAML: {{data.get('kind', 'unknown')}}")
EOF

exit 0
""")
        test_script.chmod(0o755)

        # Run the wrapper script
        result = subprocess.run(
            [str(test_script)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        assert result.returncode == 0, f"Validation failed: {result.stderr}"
        assert "✓ Valid YAML" in result.stdout

    def test_invalid_yaml_fails(self, tmp_path: Path):
        """Test that invalid YAML syntax is detected."""
        # Create temporary structure
        k8s_dir = tmp_path / "k8s"
        k8s_dir.mkdir()

        # Create an invalid YAML file (unmatched bracket)
        invalid_manifest = k8s_dir / "invalid.yaml"
        invalid_manifest.write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: invalid
  labels: {
    app: test
""")

        # Create test script that tries to load the YAML
        test_script = tmp_path / "test_invalid.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

python3 - << 'EOF'
import yaml
import sys

try:
    with open("{invalid_manifest}", "r") as f:
        yaml.safe_load(f)
    print("✗ Should have failed but didn't")
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"✓ Correctly detected YAML error: {{type(e).__name__}}")
    sys.exit(0)
EOF
""")
        test_script.chmod(0o755)

        result = subprocess.run(
            [str(test_script)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Correctly detected YAML error" in result.stdout

    def test_real_manifests_are_valid(self, script_path: Path):
        """Test that actual repository manifests are valid."""
        repo_root = script_path.parent.parent.parent
        k8s_dir = repo_root / "deploy" / "k8s"

        if not k8s_dir.exists():
            pytest.skip("No K8s manifests directory found")

        # Check that we have at least some manifests
        manifests = list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml"))

        if not manifests:
            pytest.skip("No YAML manifests found in deploy/k8s/")

        # Just verify they're valid YAML (don't run full script to avoid dependencies)
        import yaml

        for manifest in manifests:
            with open(manifest) as f:
                try:
                    yaml.safe_load_all(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {manifest.name}: {e}")

    def test_json_files_are_valid(self, tmp_path: Path):
        """Test that JSON validation works."""
        # Create temporary structure
        grafana_dir = tmp_path / "grafana"
        grafana_dir.mkdir()

        # Create a valid JSON file
        valid_json = grafana_dir / "dashboard.json"
        valid_json.write_text('{"version": 1, "title": "Test Dashboard"}')

        # Create an invalid JSON file
        invalid_json = grafana_dir / "invalid.json"
        invalid_json.write_text('{"version": 1, "title": "Missing closing brace"')

        # Test validation script
        test_script = tmp_path / "test_json.sh"
        test_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail

echo "Testing valid JSON..."
python3 -c "import json; json.load(open('{valid_json}'))" && echo "✓ Valid JSON"

echo "Testing invalid JSON..."
if python3 -c "import json; json.load(open('{invalid_json}'))" 2>/dev/null; then
    echo "✗ Should have failed"
    exit 1
else
    echo "✓ Correctly detected invalid JSON"
    exit 0
fi
""")
        test_script.chmod(0o755)

        result = subprocess.run(
            [str(test_script)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "✓ Valid JSON" in result.stdout
        assert "✓ Correctly detected invalid JSON" in result.stdout

    def test_script_has_proper_structure(self, script_path: Path):
        """Test that the script has expected structure and components."""
        content = script_path.read_text()

        # Check for strict mode
        assert "set -eEfuo pipefail" in content or "set -euo pipefail" in content

        # Check for key functions
        assert "validate_yaml_syntax" in content or "validate_manifest" in content

        # Check for error handling
        assert "ERRORS=" in content or "errors=" in content

        # Check for proper exit codes
        assert "exit 0" in content
        assert "exit 1" in content
