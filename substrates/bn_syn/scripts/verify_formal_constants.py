#!/usr/bin/env python3
"""Verify formal specification constants match code reality.

This governance gate ensures that formal verification models (TLA+, Coq) use
the same constants as the actual code, preventing spec drift.

Checks:
1. TLA+ BNsyn.cfg constants vs src/bnsyn/config.py
2. Coq BNsyn_Sigma.v constants vs src/bnsyn/config.py

Usage:
    python -m scripts.verify_formal_constants

Exit codes:
    0: All constants match
    1: Mismatches found
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ConstantMismatch:
    """A mismatch between spec and code constants."""

    spec_type: str  # "TLA+" or "Coq"
    constant_name: str
    spec_value: Any
    code_value: Any
    code_location: str

    def __str__(self) -> str:
        return (
            f"{self.spec_type} constant '{self.constant_name}' mismatch:\n"
            f"  Spec value: {self.spec_value}\n"
            f"  Code value: {self.code_value}\n"
            f"  Code location: {self.code_location}"
        )


class FormalConstantsVerifier:
    """Verify formal spec constants match code."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.mismatches: list[ConstantMismatch] = []

    def extract_python_constants(self) -> dict[str, tuple[Any, str]]:
        """Extract constants from Python code.

        Returns:
            Dict mapping constant name to (value, location)
        """
        config_path = self.repo_root / "src" / "bnsyn" / "config.py"

        if not config_path.exists():
            print(f"Warning: {config_path} not found", file=sys.stderr)
            return {}

        constants = {}

        with config_path.open() as f:
            content = f.read()

        # Extract CriticalityParams constants
        criticality_match = re.search(
            r"class CriticalityParams.*?gain_min:\s*[\w.]+\s*=\s*([\d.]+).*?"
            r"gain_max:\s*[\w.]+\s*=\s*([\d.]+)",
            content,
            re.DOTALL,
        )

        if criticality_match:
            constants["GainMin"] = (
                float(criticality_match.group(1)),
                "src/bnsyn/config.py:CriticalityParams.gain_min",
            )
            constants["GainMax"] = (
                float(criticality_match.group(2)),
                "src/bnsyn/config.py:CriticalityParams.gain_max",
            )

        # Extract TemperatureParams constants
        temp_match = re.search(
            r"class TemperatureParams.*?"
            r"T0:\s*[\w.]+\s*=\s*([\d.e-]+).*?"
            r"Tmin:\s*[\w.]+\s*=\s*([\d.e-]+).*?"
            r"alpha:\s*[\w.]+\s*=.*?default=([\d.]+).*?"
            r"Tc:\s*[\w.]+\s*=\s*([\d.]+).*?"
            r"gate_tau:\s*[\w.]+\s*=\s*([\d.]+)",
            content,
            re.DOTALL,
        )

        if temp_match:
            constants["T0"] = (
                float(temp_match.group(1)),
                "src/bnsyn/config.py:TemperatureParams.T0",
            )
            constants["Tmin"] = (
                float(temp_match.group(2)),
                "src/bnsyn/config.py:TemperatureParams.Tmin",
            )
            constants["Alpha"] = (
                float(temp_match.group(3)),
                "src/bnsyn/config.py:TemperatureParams.alpha",
            )
            constants["Tc"] = (
                float(temp_match.group(4)),
                "src/bnsyn/config.py:TemperatureParams.Tc",
            )
            constants["GateTau"] = (
                float(temp_match.group(5)),
                "src/bnsyn/config.py:TemperatureParams.gate_tau",
            )

        return constants

    def extract_tla_constants(self) -> dict[str, Any]:
        """Extract constants from TLA+ config file.

        Returns:
            Dict mapping constant name to value
        """
        cfg_path = self.repo_root / "specs" / "tla" / "BNsyn.cfg"

        if not cfg_path.exists():
            print(f"Warning: {cfg_path} not found", file=sys.stderr)
            return {}

        constants = {}

        with cfg_path.open() as f:
            in_constants = False
            for line in f:
                line = line.strip()

                if line.startswith("CONSTANTS"):
                    in_constants = True
                    continue

                if in_constants:
                    # Stop at next section
                    if line.startswith("\\*") and "INVARIANTS" in line:
                        break
                    if line.startswith("INVARIANTS"):
                        break
                    if line.startswith("PROPERTIES"):
                        break
                    if line.startswith("CONSTRAINT"):
                        break

                    # Parse constant definition: Name = Value
                    match = re.match(r"(\w+)\s*=\s*([\d.e-]+)", line)
                    if match:
                        name, value = match.groups()
                        try:
                            constants[name] = float(value)
                        except ValueError:
                            constants[name] = value

        return constants

    def extract_coq_constants(self) -> dict[str, Any]:
        """Extract constants from Coq proof file.

        Returns:
            Dict mapping constant name to value
        """
        coq_path = self.repo_root / "specs" / "coq" / "BNsyn_Sigma.v"

        if not coq_path.exists():
            print(f"Warning: {coq_path} not found", file=sys.stderr)
            return {}

        constants = {}

        with coq_path.open() as f:
            content = f.read()

        # Extract gain_min and gain_max definitions
        gain_min_match = re.search(r"Definition\s+gain_min\s*:\s*R\s*:=\s*([\d.]+)\.?", content)
        if gain_min_match:
            # Remove trailing period if present
            value_str = gain_min_match.group(1).rstrip(".")
            constants["gain_min"] = float(value_str)

        gain_max_match = re.search(r"Definition\s+gain_max\s*:\s*R\s*:=\s*([\d.]+)\.?", content)
        if gain_max_match:
            # Remove trailing period if present
            value_str = gain_max_match.group(1).rstrip(".")
            constants["gain_max"] = float(value_str)

        return constants

    def verify_tla(self, code_constants: dict[str, tuple[Any, str]]) -> None:
        """Verify TLA+ constants match code."""
        tla_constants = self.extract_tla_constants()

        # Check each TLA+ constant against code
        for const_name, tla_value in tla_constants.items():
            if const_name in code_constants:
                code_value, code_location = code_constants[const_name]

                # Allow small floating point tolerance
                if isinstance(tla_value, float) and isinstance(code_value, float):
                    if abs(tla_value - code_value) > 1e-9:
                        self.mismatches.append(
                            ConstantMismatch(
                                spec_type="TLA+",
                                constant_name=const_name,
                                spec_value=tla_value,
                                code_value=code_value,
                                code_location=code_location,
                            )
                        )
                elif tla_value != code_value:
                    self.mismatches.append(
                        ConstantMismatch(
                            spec_type="TLA+",
                            constant_name=const_name,
                            spec_value=tla_value,
                            code_value=code_value,
                            code_location=code_location,
                        )
                    )

    def verify_coq(self, code_constants: dict[str, tuple[Any, str]]) -> None:
        """Verify Coq constants match code."""
        coq_constants = self.extract_coq_constants()

        # Map Coq names to code names
        mapping = {
            "gain_min": "GainMin",
            "gain_max": "GainMax",
        }

        for coq_name, code_name in mapping.items():
            if coq_name in coq_constants and code_name in code_constants:
                coq_value = coq_constants[coq_name]
                code_value, code_location = code_constants[code_name]

                # Allow small floating point tolerance
                if isinstance(coq_value, float) and isinstance(code_value, float):
                    if abs(coq_value - code_value) > 1e-9:
                        self.mismatches.append(
                            ConstantMismatch(
                                spec_type="Coq",
                                constant_name=coq_name,
                                spec_value=coq_value,
                                code_value=code_value,
                                code_location=code_location,
                            )
                        )

    def verify_all(self) -> bool:
        """Verify all formal specs against code.

        Returns:
            True if all match, False if mismatches found
        """
        print("🔍 Verifying formal specification constants...")
        print()

        # Extract code constants
        code_constants = self.extract_python_constants()

        if not code_constants:
            print("❌ Failed to extract code constants", file=sys.stderr)
            return False

        print(f"✅ Extracted {len(code_constants)} constants from code")

        # Verify TLA+
        self.verify_tla(code_constants)

        # Verify Coq
        self.verify_coq(code_constants)

        # Report results
        print()
        if self.mismatches:
            print(f"❌ Found {len(self.mismatches)} constant mismatches:")
            print()
            for mismatch in self.mismatches:
                print(f"  {mismatch}")
                print()
            return False
        else:
            print("✅ All formal specification constants match code!")
            return True


def main() -> int:
    """Main entry point."""
    repo_root = Path(__file__).parent.parent

    verifier = FormalConstantsVerifier(repo_root)

    if verifier.verify_all():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
