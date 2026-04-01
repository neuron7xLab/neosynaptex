from __future__ import annotations

import os

from hypothesis import Verbosity, settings

settings.register_profile(
    "quick",
    max_examples=100,
    deadline=5000,
    print_blob=True,
    derandomize=True,
)
settings.register_profile(
    "thorough",
    max_examples=1000,
    deadline=20000,
    print_blob=True,
    derandomize=True,
)
settings.register_profile(
    "ci",
    max_examples=50,
    deadline=5000,
    verbosity=Verbosity.verbose,
    print_blob=True,
    derandomize=True,
)

profile_name = os.getenv("HYPOTHESIS_PROFILE")
if profile_name:
    settings.load_profile(profile_name)
    print(f"[Hypothesis] Loaded profile: {profile_name} (from HYPOTHESIS_PROFILE env var)")
elif os.getenv("CI"):
    settings.load_profile("ci")
    print("[Hypothesis] Loaded profile: ci (CI mode)")
else:
    print("[Hypothesis] Using default profile")
