"""Tests for Hypothesis profile configuration in property contour."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


pytestmark = pytest.mark.property


def test_hypothesis_profile_env_var_must_be_valid() -> None:
    profile = os.getenv("HYPOTHESIS_PROFILE")

    if not profile:
        return

    valid_profiles = {"quick", "thorough", "ci"}

    if profile not in valid_profiles:
        raise ValueError(
            f"HYPOTHESIS_PROFILE={profile!r} is not a valid profile. "
            f"Valid profiles: {', '.join(sorted(valid_profiles))}. "
            f"Update tests/properties/conftest.py if you need to add a new profile."
        )


def test_hypothesis_profile_loads_without_error() -> None:
    profile = os.getenv("HYPOTHESIS_PROFILE")

    if not profile:
        return

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/properties", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    output = result.stdout + result.stderr

    if "hypothesis.errors.InvalidArgument" in output:
        raise AssertionError(f"Hypothesis profile error detected:\n{output}")

    if "Failed to load profile" in output:
        raise AssertionError(f"Failed to load Hypothesis profile:\n{output}")
