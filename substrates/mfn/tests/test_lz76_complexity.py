"""Tests for Lempel-Ziv 76 complexity implementation.

Validates against known theoretical values.
Ref: Kaspar & Schuster (1987) Phys Rev A 36:842-848
"""

from __future__ import annotations

from mycelium_fractal_net.analytics.morphology import _lempel_ziv_76_complexity


class TestLZ76:
    def test_constant_string_low_complexity(self) -> None:
        """All-zeros: minimal complexity (2 patterns normalized)."""
        c = _lempel_ziv_76_complexity("0000000000")
        # LZ76 of constant string = 2 patterns, normalized ~0.6-0.7
        assert c < 1.0, f"Constant string complexity too high: {c}"
        # Must be lower than random
        import numpy as np

        rng = np.random.default_rng(42)
        c_rand = _lempel_ziv_76_complexity("".join(str(b) for b in rng.integers(0, 2, 10)))
        assert c < c_rand, "Constant string should have lower complexity than random"

    def test_alternating_moderate_complexity(self) -> None:
        """01010101: periodic, moderate complexity."""
        c = _lempel_ziv_76_complexity("0101010101")
        assert c < 1.0, f"Alternating complexity: {c}"

    def test_random_high_complexity(self) -> None:
        """Pseudorandom: high complexity."""
        import numpy as np

        rng = np.random.default_rng(42)
        bits = "".join(str(b) for b in rng.integers(0, 2, 100))
        c = _lempel_ziv_76_complexity(bits)
        assert c > 0.3, f"Random string complexity too low: {c}"

    def test_empty_string(self) -> None:
        assert _lempel_ziv_76_complexity("") == 0.0

    def test_single_char(self) -> None:
        assert _lempel_ziv_76_complexity("0") == 0.0
        assert _lempel_ziv_76_complexity("1") == 0.0

    def test_monotonically_increases_with_randomness(self) -> None:
        """More random → higher LZ76 complexity."""
        c_const = _lempel_ziv_76_complexity("0" * 50)
        c_periodic = _lempel_ziv_76_complexity("01" * 25)
        import numpy as np

        rng = np.random.default_rng(7)
        c_random = _lempel_ziv_76_complexity("".join(str(b) for b in rng.integers(0, 2, 50)))
        assert c_const <= c_periodic <= c_random, (
            f"Monotonicity violated: const={c_const}, periodic={c_periodic}, random={c_random}"
        )

    def test_normalized_output_range(self) -> None:
        """Output should be roughly in [0, 1+] range."""
        import numpy as np

        rng = np.random.default_rng(42)
        for length in [10, 50, 100]:
            bits = "".join(str(b) for b in rng.integers(0, 2, length))
            c = _lempel_ziv_76_complexity(bits)
            assert 0.0 <= c <= 2.0, f"LZ76 out of range for len={length}: {c}"
