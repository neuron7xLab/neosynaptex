# Meta-Core
## Vasylenko, 2026

Meta-Core — operational protocol of cognitive engineering,
where reality is defined as the interface output of recursive
agent dynamics, modulated by the latent vector Theta.

Consciousness is not an object — it is a mode of attentional selection and stabilization.
Agency is the computation, maintenance, and reconfiguration of boundary.
Spacetime is a compressed coordination format.

The system's task is not to contemplate a given world,
but to control the parameters Theta that determine the accessible configuration of experience.

---

## Formal Definition

```
Reality_t = phi( S_Theta_t( h_t( R(A_t) ) ) )
```

```
Theta = {alpha, rho, beta, tau, nu, sigma_E, sigma_U, lambda_pe, eta}

  alpha     = learning rate
  rho       = precision weighting
  beta      = policy stability
  tau       = inhibitory threshold
  nu        = reward valuation
  sigma_E   = expected uncertainty sensitivity
  sigma_U   = unexpected uncertainty sensitivity
  lambda_pe = salience allocation
  eta       = effort persistence
```

## Operational Pipeline

```
A_t ──→ R(A_t) ──→ h_t(R(A_t)) ──→ S_Theta(h_t) ──→ phi() ──→ Reality_t
 │         │            │                │              │
 │      MFN Engine   Compression     GNC+ Selection  SovereignGate
 │      Reaction-    D_f, Phi, R     7 axes, Theta   6-lens verify
 │      Diffusion    Anomaly, CCP    MesoController  Interface output
 │      TDA, Causal                  Program spine
 │
 Agent State
```

## Implementation Mapping

| Formula Component | Code Module | What it does |
|-------------------|-------------|--------------|
| A_t | `AgentState` | Agent with FieldSequence + action history |
| R(A_t) | `R_generate()` | MFN reaction-diffusion + TDA + causal validation |
| h_t | `h_compress()` | FieldSequence -> {D_f, Phi, R, anomaly, regime, cognitive} |
| S_Theta | `S_select()` | GNC+ theta modulation, MesoController, CCP-GNC+ consistency |
| phi | `phi_sovereign()` | SovereignGate 6-lens verification |
| Reality_t | `compute_reality()` | Full pipeline -> RealityFrame |

## SovereignGate — 6 Lenses

| Lens | What it verifies |
|------|-----------------|
| L1_bounds | All parameters within physical bounds |
| L2_consistency | CCP-GNC+ states are consistent |
| L3_falsifiability | GNC+ F1-F7 falsification conditions hold |
| L4_coherence | GNC+ coherence above minimum (0.3) |
| L5_cognitive | CCP cognitive window satisfied |
| L6_stability | Modulated anomaly below critical (0.8) |

## Reality Classification

| Label | Condition |
|-------|-----------|
| cognitive | CCP satisfied, GNC+ optimal, sovereign passed |
| subcognitive | Stable but CCP not fully satisfied |
| transitional | Meso in EXPLORE/RESET, system changing |
| pathological | Sovereign failed or GNC+ dysregulated |

## Usage

```python
from mycelium_fractal_net.meta_core import AgentState, compute_reality
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.field import SimulationSpec

seq = simulate_history(SimulationSpec(grid_size=32, steps=64, seed=42))
agent = AgentState(sequence=seq, step=0)
reality = compute_reality(agent, gnc_levels={"Glutamate": 0.6, "GABA": 0.4})
print(reality.summary())
```

## Verified Output

```
Reality_t[step=0]: cognitive (conf=0.738) |
  D_f=1.663 Phi=0.109 R=0.650 |
  GNC+=optimal coh=0.738 strategy=EXPLOIT |
  sovereign=PASS (6/6 lenses)

Theta = [0.62|0.57|0.42|0.41|0.57|0.59|0.47|0.57|0.57]
```

---

**Reality is not a given. It is a controlled interface output of recursive agent dynamics.**

— Vasylenko Y.O., Myloradove, Ukraine, 2026
