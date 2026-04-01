#!/usr/bin/env python3
"""Quick verification benchmark for LyapunovAnalyzer optimization.

Vasylenko (2026) | O(N^4) -> O(N^2) via analytical Jacobian registry.
"""

import gc
import time

import numpy as np

from mycelium_fractal_net.core.thermodynamic_kernel import LyapunovAnalyzer


def gray_scott_rxn(
    u: np.ndarray, v: np.ndarray, F: float = 0.04, k: float = 0.06,
) -> tuple[np.ndarray, np.ndarray]:
    return (-u * v**2 + F * (1 - u), u * v**2 - (F + k) * v)


la = LyapunovAnalyzer()

print("=== LyapunovAnalyzer Speedup Verification ===\n")
print(f"{'Grid':12} {'Method':20} {'Median ms':12} {'Status':10}")
print("-" * 56)

TARGETS = {16: 1.0, 32: 2.0, 64: 10.0, 128: 50.0}

for N in [16, 32, 64, 128]:
    rng = np.random.default_rng(42)
    u = rng.random((N, N))
    v = rng.random((N, N)) * 0.3

    # Warmup
    for _ in range(3):
        la.leading_lyapunov_exponent(u, v, gray_scott_rxn)

    gc.disable()
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        la.leading_lyapunov_exponent(u, v, gray_scott_rxn)
        times.append((time.perf_counter() - t0) * 1000)
    gc.enable()

    median = float(np.median(times))
    target = TARGETS[N]
    status = "PASS" if median < target * 2 else "FAIL"

    print(f"{N}x{N:9} {la.last_method:20} {median:10.3f}ms {status:10}")

print("\n=== Correctness Check (32x32, analytical vs numerical) ===")
rng = np.random.default_rng(42)
u32 = rng.random((32, 32))
v32 = rng.random((32, 32)) * 0.3

lam_analytical = la.leading_lyapunov_exponent(u32, v32, gray_scott_rxn)
spectrum_num = la._numerical_fd_spectrum(u32, v32, gray_scott_rxn)
lam_numerical = float(spectrum_num[0])

print(f"  Analytical  lambda_1 = {lam_analytical:.6f}")
print(f"  Numerical   lambda_1 = {lam_numerical:.6f}")
print(f"  Diff                 = {abs(lam_analytical - lam_numerical):.6f}")
print(f"  Within 0.5           = {'YES' if abs(lam_analytical - lam_numerical) < 0.5 else 'NO'}")
