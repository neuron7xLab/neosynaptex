"""Single source of truth for all release claims.

Every number in README, CLI, tests, and docs MUST come from here.
No magic numbers anywhere else in the codebase.
"""

from __future__ import annotations

from typing import Any

__all__ = ["CONTRACT", "ReleaseContract"]

CAUSAL_RULE_COUNT = 46
CAUSAL_STAGE_COUNT = 7
FEATURE_DIM = 57
GOLDEN_HASH_PROFILES = 4
BIO_MECHANISMS = 8
INVARIANTS_PROVEN = 3

SUPPORTED_PYTHONS = ("3.10", "3.11", "3.12", "3.13")
PYTHON_MIN = "3.10"
PYTHON_MAX = "3.13"

INSTALL_TIERS = {
    "core": {
        "command": "pip install mycelium-fractal-net",
        "deps": ["numpy", "pydantic"],
        "description": "Simulation + detection + diagnosis (numpy + pydantic)",
    },
    "bio": {
        "command": "pip install mycelium-fractal-net[bio]",
        "deps": ["scipy", "scikit-learn", "cmaes"],
        "description": "Biological mechanisms: Physarum, FHN, chemotaxis, Levin",
    },
    "science": {
        "command": "pip install mycelium-fractal-net[science]",
        "deps": ["scipy", "gudhi", "POT"],
        "description": "TDA, optimal transport, causal emergence, invariants",
    },
    "full": {
        "command": "pip install mycelium-fractal-net[full]",
        "deps": ["bio", "science", "api", "ml", "accel", "frontier", "data"],
        "description": "Everything",
    },
}

VERIFY_TARGETS = {
    "verify-core": {
        "command": "make verify-core",
        "markers": "-m core",
        "description": "Core tests only (no optional deps)",
    },
    "verify-bio": {
        "command": "make verify-bio",
        "markers": "-m 'core or bio'",
        "description": "Core + bio tests",
    },
    "verify-science": {
        "command": "make verify-science",
        "markers": "-m 'core or science'",
        "description": "Core + science tests",
    },
    "verify-full": {
        "command": "make verify-full",
        "markers": "",
        "description": "All tests",
    },
}


class ReleaseContract:
    """Queryable release contract — use CONTRACT singleton."""

    causal_rules = CAUSAL_RULE_COUNT
    causal_stages = CAUSAL_STAGE_COUNT
    feature_dim = FEATURE_DIM
    golden_profiles = GOLDEN_HASH_PROFILES
    bio_mechanisms = BIO_MECHANISMS
    invariants = INVARIANTS_PROVEN
    python_min = PYTHON_MIN
    python_max = PYTHON_MAX
    supported_pythons = SUPPORTED_PYTHONS
    install_tiers = INSTALL_TIERS
    verify_targets = VERIFY_TARGETS

    def to_dict(self) -> dict[str, Any]:
        return {
            "causal_rules": self.causal_rules,
            "causal_stages": self.causal_stages,
            "feature_dim": self.feature_dim,
            "golden_profiles": self.golden_profiles,
            "bio_mechanisms": self.bio_mechanisms,
            "invariants": self.invariants,
            "python_min": self.python_min,
            "python_max": self.python_max,
            "install_tiers": list(self.install_tiers.keys()),
            "verify_targets": list(self.verify_targets.keys()),
        }

    def info_text(self) -> str:
        lines = [
            "MyceliumFractalNet Release Contract",
            f"  Causal rules:    {self.causal_rules}",
            f"  Feature dims:    {self.feature_dim}",
            f"  Golden profiles: {self.golden_profiles}",
            f"  Bio mechanisms:  {self.bio_mechanisms}",
            f"  Invariants:      {self.invariants}",
            f"  Python:          {self.python_min}–{self.python_max}",
            f"  Install tiers:   {', '.join(self.install_tiers)}",
            f"  Verify targets:  {', '.join(self.verify_targets)}",
        ]
        return "\n".join(lines)


CONTRACT = ReleaseContract()
