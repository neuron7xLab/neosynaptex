#!/usr/bin/env python3
"""
Theta-SWR State Switching Example

Demonstrates:
- State machine
- Replay detection
- Gating modulation
"""
import numpy as np

from core.theta_swr_switching import (
    NetworkState,
    NetworkStateController,
    ReplayDetector,
    StateTransitionParams,
)

np.random.seed(42)

print("=" * 70)
print("THETA-SWR STATE SWITCHING EXAMPLE")
print("=" * 70)

# Create controller
params = StateTransitionParams(
    P_theta_to_SWR=0.005, P_SWR_to_theta=0.05, SWR_duration_mean=60.0, SWR_duration_std=15.0
)

controller = NetworkStateController(params, dt=0.1)
detector = ReplayDetector()

# Simulate 10 seconds
T = 10000.0
n_steps = int(T / 0.1)

theta_time = 0.0
swr_time = 0.0
swr_events = 0

print("\nSimulating 10 seconds...")
for step in range(n_steps):
    t = step * 0.1
    state, changed = controller.step()

    if state == NetworkState.THETA:
        theta_time += 0.1
    elif state == NetworkState.SWR:
        swr_time += 0.1
        if changed:
            swr_events += 1

print("\nResults:")
print(f"  Theta time: {theta_time:.1f}ms ({theta_time/T*100:.1f}%)")
print(f"  SWR time: {swr_time:.1f}ms ({swr_time/T*100:.1f}%)")
print(f"  SWR events: {swr_events}")

# Test gating
controller.state = NetworkState.THETA
print("\nTheta mode:")
print(f"  Inhibition: {controller.get_inhibition_factor():.2f}")
print(f"  Recurrence: {controller.get_recurrence_factor():.2f}")

controller.state = NetworkState.SWR
print("\nSWR mode:")
print(f"  Inhibition: {controller.get_inhibition_factor():.2f} (reduced!)")
print(f"  Recurrence: {controller.get_recurrence_factor():.2f} (boosted!)")

print("\n✅ Example complete!")
