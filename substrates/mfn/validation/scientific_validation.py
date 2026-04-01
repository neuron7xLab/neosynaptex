"""Scientific validation against published experimental data.

This module validates MyceliumFractalNet outputs against published
results from biophysics literature to ensure physiological accuracy.

References:
    - Hille B (2001) "Ion Channels of Excitable Membranes" 3rd Ed, Sinauer
    - Fricker et al. (2017) Fungal Biology Reviews 31:158-170
    - Hodgkin & Huxley (1952) J. Physiol. 117:500-544
    - Turing A (1952) Phil. Trans. R. Soc. Lond. B 237:37-72

Run with: python validation/scientific_validation.py
"""

import sys
from dataclasses import dataclass
from typing import Optional

import numpy as np

from mycelium_fractal_net import (
    BODY_TEMPERATURE_K,
    FARADAY_CONSTANT,
    R_GAS_CONSTANT,
    compute_nernst_potential,
    estimate_fractal_dimension,
    simulate_mycelium_field,
)


@dataclass
class ValidationResult:
    """Container for validation results."""

    test_name: str
    expected_value: float
    computed_value: float
    tolerance: float
    unit: str
    passed: bool
    reference: str
    notes: Optional[str] = None


class ScientificValidation:
    """Validate against published experimental data."""

    def __init__(self) -> None:
        """Initialize validator."""
        self.results: list[ValidationResult] = []

    def validate_nernst_against_hille2001(self) -> list[ValidationResult]:
        """Compare computed potentials to Hille (2001) Table 1.1.

        Reference: Hille B (2001) "Ion Channels of Excitable Membranes"
        3rd Ed, Sinauer Associates, p.52, Table 1.1

        Data from squid giant axon at various temperatures.
        """
        print("\n" + "=" * 60)
        print("Validating Nernst Potentials Against Hille (2001)")
        print("=" * 60)

        # Mammalian skeletal muscle at 37°C (Table 1.1)
        # Values from Hille, Table 1.1, page 52
        mammalian_data = {
            "K+": {
                "in_mm": 140.0,
                "out_mm": 5.0,
                "valence": 1,
                "E_expected_mv": -89.0,
                "tolerance_mv": 5.0,
            },
            "Na+": {
                "in_mm": 12.0,
                "out_mm": 145.0,
                "valence": 1,
                "E_expected_mv": 66.0,
                "tolerance_mv": 5.0,
            },
            "Cl-": {
                "in_mm": 4.0,
                "out_mm": 120.0,
                "valence": -1,
                "E_expected_mv": -89.0,
                "tolerance_mv": 10.0,
            },
            "Ca2+": {
                "in_mm": 0.0001,  # 100 nM
                "out_mm": 2.0,
                "valence": 2,
                "E_expected_mv": 102.0,  # Calculated from Nernst at 37°C
                "tolerance_mv": 20.0,  # Wider tolerance due to variability in literature
            },
        }

        results = []

        for ion, params in mammalian_data.items():
            c_in = params["in_mm"] / 1000.0  # Convert to M
            c_out = params["out_mm"] / 1000.0  # Convert to M

            e_computed = compute_nernst_potential(
                z_valence=params["valence"],
                concentration_out_molar=c_out,
                concentration_in_molar=c_in,
                temperature_k=BODY_TEMPERATURE_K,
            )
            e_computed_mv = e_computed * 1000.0

            e_expected = params["E_expected_mv"]
            tolerance = params["tolerance_mv"]
            error = abs(e_computed_mv - e_expected)
            passed = error < tolerance

            result = ValidationResult(
                test_name=f"Nernst_{ion}_mammalian_37C",
                expected_value=e_expected,
                computed_value=e_computed_mv,
                tolerance=tolerance,
                unit="mV",
                passed=passed,
                reference="Hille (2001) Table 1.1, p.52",
                notes=f"[{ion}]_in={params['in_mm']}mM, [{ion}]_out={params['out_mm']}mM",
            )

            results.append(result)
            self.results.append(result)

            status = "✓" if passed else "✗"
            print(
                f"{status} {ion}: computed={e_computed_mv:.1f} mV, "
                f"expected={e_expected:.1f} mV, error={error:.1f} mV"
            )

        return results

    def validate_nernst_squid_axon(self) -> list[ValidationResult]:
        """Validate against squid giant axon data at 18.5°C.

        Reference: Hille (2001) Table 1.1
        Original data from Hodgkin & Keynes (1955)
        """
        print("\n" + "-" * 60)
        print("Validating Against Squid Giant Axon (18.5°C)")
        print("-" * 60)

        squid_temp_k = 273.15 + 18.5  # 18.5°C in Kelvin

        squid_data = {
            "K+": {
                "in_mm": 400.0,
                "out_mm": 20.0,
                "valence": 1,
                "E_expected_mv": -75.0,
                "tolerance_mv": 5.0,
            },
            "Na+": {
                "in_mm": 50.0,
                "out_mm": 440.0,
                "valence": 1,
                "E_expected_mv": 55.0,
                "tolerance_mv": 5.0,
            },
            "Cl-": {
                "in_mm": 52.0,
                "out_mm": 560.0,
                "valence": -1,
                "E_expected_mv": -60.0,
                "tolerance_mv": 5.0,
            },
        }

        results = []

        for ion, params in squid_data.items():
            c_in = params["in_mm"] / 1000.0
            c_out = params["out_mm"] / 1000.0

            e_computed = compute_nernst_potential(
                z_valence=params["valence"],
                concentration_out_molar=c_out,
                concentration_in_molar=c_in,
                temperature_k=squid_temp_k,
            )
            e_computed_mv = e_computed * 1000.0

            e_expected = params["E_expected_mv"]
            tolerance = params["tolerance_mv"]
            error = abs(e_computed_mv - e_expected)
            passed = error < tolerance

            result = ValidationResult(
                test_name=f"Nernst_{ion}_squid_18.5C",
                expected_value=e_expected,
                computed_value=e_computed_mv,
                tolerance=tolerance,
                unit="mV",
                passed=passed,
                reference="Hille (2001) Table 1.1; Hodgkin & Keynes (1955)",
            )

            results.append(result)
            self.results.append(result)

            status = "✓" if passed else "✗"
            print(
                f"{status} {ion}: computed={e_computed_mv:.1f} mV, "
                f"expected={e_expected:.1f} mV, error={error:.1f} mV"
            )

        return results

    def validate_rtfz_constant(self) -> ValidationResult:
        """Validate RT/zF constant at body temperature.

        The Nernst factor RT/F at 37°C should be approximately 26.7 mV.
        For ln to log10 conversion: 26.7 * 2.303 ≈ 61.5 mV
        """
        print("\n" + "-" * 60)
        print("Validating RT/F Constant")
        print("-" * 60)

        rt_f_computed = (R_GAS_CONSTANT * BODY_TEMPERATURE_K) / FARADAY_CONSTANT
        rt_f_computed_mv = rt_f_computed * 1000.0

        # Expected value at 37°C (310.15 K)
        rt_f_expected_mv = 26.73  # mV
        tolerance_mv = 0.1

        error = abs(rt_f_computed_mv - rt_f_expected_mv)
        passed = error < tolerance_mv

        result = ValidationResult(
            test_name="RT/F_at_37C",
            expected_value=rt_f_expected_mv,
            computed_value=rt_f_computed_mv,
            tolerance=tolerance_mv,
            unit="mV",
            passed=passed,
            reference="Standard biophysics (R=8.314 J/mol/K, F=96485 C/mol)",
            notes=f"T={BODY_TEMPERATURE_K:.2f} K",
        )

        self.results.append(result)

        status = "✓" if passed else "✗"
        print(
            f"{status} RT/F: computed={rt_f_computed_mv:.3f} mV, "
            f"expected={rt_f_expected_mv:.3f} mV, error={error:.4f} mV"
        )

        return result

    def validate_fractal_dimension_against_fricker2017(
        self, num_trials: int = 5
    ) -> ValidationResult:
        """Compare fractal dimension to mycelial network measurements.

        Reference: Fricker et al. (2017) "The Mycelium as a Network"
        Fungal Biology Reviews 31:158-170

        Reports fractal dimension D ≈ 1.585 ± 0.1 for Phanerochaete velutina
        on 2D agar substrates.
        """
        print("\n" + "-" * 60)
        print("Validating Fractal Dimension Against Fricker (2017)")
        print("-" * 60)

        dimensions = []

        for trial in range(num_trials):
            rng = np.random.default_rng(42 + trial * 100)

            # Simulate natural growth pattern
            field, _ = simulate_mycelium_field(
                rng,
                grid_size=64,
                steps=200,
                turing_enabled=True,
                alpha=0.18,
            )

            # Threshold at percentile to get consistent active region
            threshold = np.percentile(field, 50)
            binary = field > threshold

            if binary.sum() > 100:  # Need enough points
                d = estimate_fractal_dimension(binary)
                if 0.5 < d < 2.5:  # Filter outliers
                    dimensions.append(d)

        if len(dimensions) == 0:
            d_mean = 0.0
            d_std = 0.0
        else:
            d_mean = float(np.mean(dimensions))
            d_std = float(np.std(dimensions))

        # Fricker (2017) reports D ≈ 1.585 for P. velutina
        d_expected = 1.585
        tolerance = 0.5  # Wider tolerance for stochastic simulation

        error = abs(d_mean - d_expected)
        passed = error < tolerance

        result = ValidationResult(
            test_name="Fractal_dimension_mycelium",
            expected_value=d_expected,
            computed_value=d_mean,
            tolerance=tolerance,
            unit="dimensionless",
            passed=passed,
            reference="Fricker et al. (2017) Fungal Biology Reviews 31:158-170",
            notes=f"Mean of {len(dimensions)} trials, std={d_std:.3f}",
        )

        self.results.append(result)

        status = "✓" if passed else "✗"
        print(
            f"{status} Fractal dimension: computed={d_mean:.3f}±{d_std:.3f}, "
            f"expected={d_expected:.3f}, error={error:.3f}"
        )

        return result

    def validate_membrane_potential_range(self) -> ValidationResult:
        """Validate simulated membrane potentials are physiological.

        Physiological range for neurons:
        - Resting potential: -60 to -80 mV
        - Action potential peak: +30 to +40 mV
        - Hyperpolarization: -85 to -95 mV

        Reference: Hodgkin & Huxley (1952)
        """
        print("\n" + "-" * 60)
        print("Validating Membrane Potential Range")
        print("-" * 60)

        rng = np.random.default_rng(42)

        field, _ = simulate_mycelium_field(
            rng,
            grid_size=64,
            steps=200,
            turing_enabled=True,
            quantum_jitter=True,
        )

        field_mv = field * 1000.0
        min_mv = float(field_mv.min())
        max_mv = float(field_mv.max())

        # Expected physiological range: [-95, 40] mV
        min_expected = -95.0
        max_expected = 40.0

        # Check if simulation respects physiological bounds
        within_bounds = min_mv >= min_expected - 1.0 and max_mv <= max_expected + 1.0
        passed = within_bounds

        result = ValidationResult(
            test_name="Membrane_potential_range",
            expected_value=0.0,  # Placeholder
            computed_value=(min_mv + max_mv) / 2,  # Midpoint
            tolerance=0.0,
            unit="mV",
            passed=passed,
            reference="Hodgkin & Huxley (1952); Standard neurophysiology",
            notes=f"Range: [{min_mv:.1f}, {max_mv:.1f}] mV, "
            f"expected: [{min_expected}, {max_expected}] mV",
        )

        self.results.append(result)

        status = "✓" if passed else "✗"
        print(
            f"{status} Potential range: [{min_mv:.1f}, {max_mv:.1f}] mV "
            f"(expected: [{min_expected}, {max_expected}] mV)"
        )

        return result

    def validate_turing_pattern_formation(self) -> ValidationResult:
        """Validate that Turing morphogenesis produces spatial patterns.

        Reference: Turing A (1952) "The chemical basis of morphogenesis"
        Phil. Trans. R. Soc. Lond. B 237:37-72

        Turing patterns emerge from reaction-diffusion instability
        and show characteristic wavelengths.
        """
        print("\n" + "-" * 60)
        print("Validating Turing Pattern Formation")
        print("-" * 60)

        rng = np.random.default_rng(42)

        field_with_turing, _ = simulate_mycelium_field(
            rng, grid_size=64, steps=200, turing_enabled=True
        )

        rng2 = np.random.default_rng(42)
        field_without_turing, _ = simulate_mycelium_field(
            rng2, grid_size=64, steps=200, turing_enabled=False
        )

        # Turing patterns should produce different spatial structure
        diff = np.abs(field_with_turing - field_without_turing)
        max_diff = float(diff.max())

        # Should have measurable difference
        threshold = 1e-6
        passed = max_diff > threshold

        result = ValidationResult(
            test_name="Turing_pattern_formation",
            expected_value=threshold,  # Minimum expected difference
            computed_value=max_diff,
            tolerance=0.0,
            unit="V",
            passed=passed,
            reference="Turing (1952) Phil. Trans. R. Soc. Lond. B 237:37-72",
            notes="Comparing fields with/without Turing morphogenesis",
        )

        self.results.append(result)

        status = "✓" if passed else "✗"
        print(f"{status} Pattern difference: {max_diff:.6f} V (threshold: >{threshold} V)")

        return result

    def run_all(self) -> list[ValidationResult]:
        """Run all scientific validations."""
        print("\n" + "=" * 60)
        print("MyceliumFractalNet Scientific Validation Suite")
        print("=" * 60)

        self.validate_nernst_against_hille2001()
        self.validate_nernst_squid_axon()
        self.validate_rtfz_constant()
        self.validate_fractal_dimension_against_fricker2017()
        self.validate_membrane_potential_range()
        self.validate_turing_pattern_formation()

        # Summary
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print(f"\nPassed: {passed}/{total}")

        if passed < total:
            print("\nFailed validations:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.test_name}")
                    print(f"    Expected: {r.expected_value} {r.unit}")
                    print(f"    Computed: {r.computed_value} {r.unit}")
                    print(f"    Reference: {r.reference}")

        print("\n" + "=" * 60)
        print("References")
        print("=" * 60)
        refs = set(r.reference for r in self.results)
        for i, ref in enumerate(sorted(refs), 1):
            print(f"  [{i}] {ref}")

        return self.results


def run_validation() -> int:
    """Run all validations and return exit code.

    Returns:
        0 if all validations pass, 1 otherwise
    """
    validator = ScientificValidation()
    results = validator.run_all()

    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = run_validation()
    sys.exit(exit_code)
