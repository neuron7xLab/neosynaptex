"""Tests that runtime claims match the release contract.

Every number in README, claims_manifest.json, and tests
MUST agree with release_contract.py.
"""

import json
from pathlib import Path

from mycelium_fractal_net.core.release_contract import CONTRACT
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.field import SimulationSpec

ROOT = Path(__file__).parent.parent


class TestContractIntegrity:
    """Contract values are self-consistent."""

    def test_causal_rules_count(self):
        """Runtime causal rule count matches contract."""
        from mycelium_fractal_net.core.rule_registry import get_registry

        actual = len(get_registry())
        assert actual == CONTRACT.causal_rules, (
            f"Contract says {CONTRACT.causal_rules} rules, but registry has {actual}"
        )

    def test_feature_dim(self):
        """Feature embedding dimension matches contract."""
        spec = SimulationSpec(grid_size=16, steps=10, seed=42)
        seq = simulate_history(spec)
        from mycelium_fractal_net.core.extract import compute_morphology_descriptor

        desc = compute_morphology_descriptor(seq)
        assert len(desc.embedding) == CONTRACT.feature_dim, (
            f"Contract says {CONTRACT.feature_dim} dims, but embedding has {len(desc.embedding)}"
        )

    def test_golden_profiles(self):
        """Golden hash profile count matches contract."""
        golden = json.loads((ROOT / "tests" / "golden_hashes.json").read_text())
        assert len(golden) == CONTRACT.golden_profiles

    def test_python_range(self):
        """Supported Python range matches pyproject.toml."""
        pyproject = (ROOT / "pyproject.toml").read_text()
        assert f">={CONTRACT.python_min}" in pyproject

    def test_install_tiers_defined(self):
        """All 4 install tiers exist."""
        assert set(CONTRACT.install_tiers.keys()) == {"core", "bio", "science", "full"}

    def test_verify_targets_defined(self):
        """All 4 verify targets exist."""
        expected = {"verify-core", "verify-bio", "verify-science", "verify-full"}
        assert set(CONTRACT.verify_targets.keys()) == expected

    def test_contract_to_dict(self):
        """Contract serializes cleanly."""
        d = CONTRACT.to_dict()
        assert d["causal_rules"] == 46
        assert d["feature_dim"] == 57

    def test_info_text(self):
        """Info text is human-readable."""
        text = CONTRACT.info_text()
        assert "46" in text
        assert "57" in text


class TestClaimsManifestSync:
    """claims_manifest.json matches release contract."""

    def test_version_matches_pyproject(self):
        manifest = json.loads((ROOT / "docs" / "contracts" / "claims_manifest.json").read_text())
        pyproject = (ROOT / "pyproject.toml").read_text()
        # Extract version from pyproject
        for line in pyproject.splitlines():
            if line.startswith("version"):
                pkg_version = line.split('"')[1]
                break
        assert manifest["engine_version"] == pkg_version

    def test_causal_rules_match(self):
        manifest = json.loads((ROOT / "docs" / "contracts" / "claims_manifest.json").read_text())
        assert manifest["metrics"]["causal_rules"] == CONTRACT.causal_rules

    def test_embedding_dims_match(self):
        manifest = json.loads((ROOT / "docs" / "contracts" / "claims_manifest.json").read_text())
        assert manifest["metrics"]["embedding_dims"] == CONTRACT.feature_dim
