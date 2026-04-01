"""Deterministic execution contract for MFN simulations.

Specifies the exact environment requirements for bit-exact reproducibility.
Golden hashes are valid ONLY within a matching DeterminismSpec.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class DeterminismSpec:
    """Environment specification for deterministic execution.

    Golden hash comparisons are valid only when the current environment
    matches this spec.  Use `DeterminismSpec.current()` to capture the
    running environment and `matches()` to compare.
    """

    os: str = "linux"
    python_major: int = 3
    python_minor: int = 12
    numpy_version: str = "2.x"
    dtype: str = "float64"
    backend: str = "cpu_numpy"
    blas: str = "openblas"
    threads: int = 1

    @classmethod
    def current(cls) -> DeterminismSpec:
        """Capture the current execution environment."""
        np_ver = np.__version__
        major = f"{np_ver.split('.')[0]}.x"

        # Detect BLAS
        blas = "unknown"
        try:
            info = np.show_config(mode="dicts")
            if isinstance(info, dict):
                blas_info = info.get("Build Dependencies", {}).get("blas", {})
                blas = blas_info.get("name", "unknown")
        except Exception:
            pass

        return cls(
            os=sys.platform,
            python_major=sys.version_info.major,
            python_minor=sys.version_info.minor,
            numpy_version=major,
            dtype="float64",
            backend="cpu_numpy",
            blas=blas,
            threads=1,
        )

    def matches(self, other: DeterminismSpec) -> tuple[bool, list[str]]:
        """Check if two specs match.  Returns (match, list_of_differences)."""
        diffs = []
        for f_name in self.__dataclass_fields__:
            v1 = getattr(self, f_name)
            v2 = getattr(other, f_name)
            if v1 != v2:
                diffs.append(f"{f_name}: {v1} != {v2}")
        return len(diffs) == 0, diffs

    def to_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


# Canonical spec for golden hash generation
CANONICAL_SPEC = DeterminismSpec(
    os="linux",
    python_major=3,
    python_minor=12,
    numpy_version="2.x",
    dtype="float64",
    backend="cpu_numpy",
    blas="openblas",
    threads=1,
)


def verify_determinism(field: np.ndarray, expected_hash: str) -> tuple[bool, str]:
    """Verify a field matches its expected golden hash."""
    actual = hashlib.sha256(field.astype(np.float64).tobytes()).hexdigest()[:16]
    return actual == expected_hash, actual
