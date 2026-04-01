#!/usr/bin/env python3
"""
SERO M0 Chaos Validation — run all 5 scenarios and verify invariants.

This is not a demo. This is a falsifiable validation suite.
Each scenario has explicit pass/fail criteria derived from the
SERO v0.5 whitepaper equations.

Usage:
    python examples/01_chaos_validation.py
"""

from neuron7x_agents.regulation.sero_m0 import (
    run_all_chaos_tests,
    print_dynamics,
)


def main() -> None:
    results = run_all_chaos_tests()

    print("\n" + "=" * 72)
    print("STRESS / THROUGHPUT DYNAMICS (ASCII sparklines)")
    print("=" * 72)

    for r in results["results"]:
        print_dynamics(r)

    print("\n" + "=" * 72)
    if results["all_pass"]:
        print("VERDICT: ALL INVARIANTS HOLD. System is safe by construction.")
    else:
        print("VERDICT: FAILURES DETECTED. Review criteria above.")
    print("=" * 72)


if __name__ == "__main__":
    main()
