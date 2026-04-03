"""Test-wide configuration: reduce bootstrap/permutation for CI speed."""

import core.gamma as _cg
import neosynaptex

# Reduce from 500 to 50 — tests verify correctness, not statistical power
neosynaptex._BOOTSTRAP_N = 50
neosynaptex._PERMUTATION_N = 50
_cg.BOOTSTRAP_N = 50
