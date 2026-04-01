# MFN Use Cases & Demo Examples

**Document Version**: 1.0  
**Target Version**: MyceliumFractalNet v4.1.0  
**Status**: Final  
**Last Updated**: 2025-11-30

---

## 1. Overview

MyceliumFractalNet (MFN) is a **fractal morphogenetic feature engine** that transforms
simulation parameters into structured feature vectors for downstream analysis and
machine learning. The examples in `examples/` demonstrate three canonical use cases:

| Example | Purpose | Key MFN Features Used |
|---------|---------|----------------------|
| `simple_simulation.py` | E2E pipeline demo | Config → Simulation → Features |
| `finance_regime_detection.py` | Financial regime analysis | Fractal dimension, Lyapunov |
| `rl_exploration.py` | RL exploration modulation | Coverage analysis, STDP |

These examples showcase MFN's role as defined in [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md):
a computational module providing fractal analysis and feature extraction without
implementing trading, portfolio management, or decision-making logic.

---

## 2. Simple Simulation (E2E Pipeline)

**File**: `examples/simple_simulation.py`

### 2.1 Purpose

Demonstrates the canonical MFN workflow:

```
Config → Simulation → Feature Extraction → Validation → Dataset Record
```

### 2.2 Pipeline Steps

1. **Compute Reference Nernst Potential**
   ```python
   e_k = compute_nernst_potential(
       z_valence=1,
       concentration_out_molar=5e-3,
       concentration_in_molar=140e-3,
       temperature_k=310.0,
   )
   # E_K ≈ -89 mV
   ```

2. **Create Configurations**
   ```python
   sim_config = make_simulation_config_demo()  # grid=32, steps=32, seed=42
   feat_config = make_feature_config_demo()    # num_scales=3, threshold=-60mV
   ```

3. **Run Simulation**
   ```python
   result = run_mycelium_simulation_with_history(sim_config)
   # result.field: (32, 32) final state
   # result.history: (32, 32, 32) time series
   # result.growth_events: int
   ```

4. **Extract Features**
   ```python
   features = compute_fractal_features(result)
   # 18 features per MFN_FEATURE_SCHEMA.md
   ```

5. **Validate & Create Record**
   ```python
   assert 0.0 <= features['D_box'] <= 2.5
   assert 0.0 <= features['f_active'] <= 1.0
   record = {"sim_id": 0, **features.values}
   ```

### 2.3 Key Features Demonstrated

| Feature | Symbol | Expected Range |
|---------|--------|----------------|
| Box-counting dimension | `D_box` | [0, 2.5] |
| Regression quality | `D_r2` | [0, 1] |
| Mean potential | `V_mean` | [-95, 40] mV |
| Active fraction | `f_active` | [0, 1] |
| Temporal stability | `T_stable` | [0, steps] |

### 2.4 Running the Example

```bash
python examples/simple_simulation.py
```

**Runtime**: ~1-2 seconds

---

## 3. Finance Regime Detection

**File**: `examples/finance_regime_detection.py`

### 3.1 Purpose

Demonstrates using MFN features for financial market regime classification:

- **HIGH_COMPLEXITY**: High fractal dimension, unstable dynamics
- **LOW_COMPLEXITY**: Low fractal dimension, stable dynamics
- **NORMAL**: Intermediate values

### 3.2 Pipeline Steps

1. **Generate Synthetic Market Data**
   ```python
   returns, labels = generate_synthetic_market_data(
       rng, num_points=500, base_volatility=0.02
   )
   # Three regimes: low_volatility, normal, high_volatility
   ```

2. **Map to MFN Field Representation**
   ```python
   field = map_returns_to_field(returns, grid_size=32)
   # Maps z-score normalized returns to membrane potential field
   ```

3. **Compute Fractal Features**
   ```python
   fractal_dim = estimate_fractal_dimension(field > threshold)
   _, lyapunov = generate_fractal_ifs(rng, num_points=5000)
   ```

4. **Classify Regime**
   ```python
   regime, confidence = classify_regime(fractal_dim, v_std, lyapunov)
   # Returns: MarketRegime enum + confidence level
   ```

### 3.3 Classification Rules

| Regime | Condition |
|--------|-----------|
| HIGH_COMPLEXITY | D_box > 1.6 OR V_std > 8.0 OR λ > 0 |
| LOW_COMPLEXITY | D_box < 1.0 AND V_std < 3.0 AND λ < -2.0 |
| NORMAL | Otherwise |

### 3.4 Key Features Used

| Feature | Interpretation |
|---------|----------------|
| `D_box` | Market complexity measure |
| `V_std` | Volatility proxy |
| `lyapunov` | Dynamical stability (λ < 0 = stable) |

### 3.5 Running the Example

```bash
python examples/finance_regime_detection.py
```

**Runtime**: ~2-3 seconds

### 3.6 Important Note

This example is a **demonstration only**. MFN provides feature extraction,
not trading signals. See [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md) for system boundaries.

---

## 4. RL Exploration

**File**: `examples/rl_exploration.py`

### 4.1 Purpose

Demonstrates using MFN features to guide exploration in reinforcement learning:

- Fractal dimension of visited states measures coverage quality
- STDP-inspired reward modulation for temporal credit assignment
- Visit-count bonuses for novel state discovery

### 4.2 Components

#### GridWorld Environment

```python
@dataclass
class GridWorldConfig:
    size: int = 10
    goal: Tuple[int, int] = (9, 9)
    start: Tuple[int, int] = (0, 0)
    obstacle_probability: float = 0.1

# Rewards: +1.0 goal, -0.5 obstacle, -0.01 step
```

#### MFN Explorer

```python
class MFNExplorer:
    def get_exploration_bonus(self, state) -> float:
        # UCB-style bonus: 0.5 / sqrt(visit_count)
        
    def modulate_epsilon(self, base_eps, episode, max_eps) -> float:
        # eps = base * decay * (1 + fractal_feedback)
        # Low D → more exploration (clustered coverage)
        
    def modulate_reward_stdp(self, t, reward) -> float:
        # STDP-inspired temporal credit assignment
```

### 4.3 Pipeline Steps

1. **Initialize Environment & Explorer**
   ```python
   env = GridWorld(config=GridWorldConfig(size=10, seed=42))
   explorer = MFNExplorer(grid_size=10, seed=42)
   ```

2. **Training Loop**
   ```python
   for episode in range(num_episodes):
       epsilon = explorer.modulate_epsilon(0.8, episode, num_episodes)
       bonus = explorer.get_exploration_bonus(state)
       
       if rng.random() < epsilon + bonus:
           action = random_action
       else:
           action = exploit_action
   ```

3. **Coverage Analysis**
   ```python
   coverage = env.get_coverage()
   visit_map = env.get_visit_map()
   fractal_dim = estimate_fractal_dimension(visit_map)
   ```

### 4.4 Key Features Used

| Feature | Role |
|---------|------|
| `estimate_fractal_dimension` | Coverage quality metric |
| `STDP_TAU_PLUS/MINUS` | Temporal credit window |
| `STDP_A_PLUS/MINUS` | Credit magnitude |

### 4.5 Running the Example

```bash
python examples/rl_exploration.py
```

**Runtime**: ~3-5 seconds

---

## 5. Extensibility: Adding New Use Cases

To add a new use case to MFN:

### 5.1 Create the Example File

```python
# examples/my_new_use_case.py
from mycelium_fractal_net import (
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
    compute_fractal_features,
)

def run_demo(*, verbose=True, return_result=False):
    """Main demo function with verbose and return options."""
    # ... implementation
```

### 5.2 Use Existing Public API

Only use functions exported from `mycelium_fractal_net.__init__`:

```python
# Configuration
make_simulation_config_demo()
make_feature_config_demo()
make_dataset_config_demo()

# Simulation
run_mycelium_simulation()
run_mycelium_simulation_with_history()
simulate_mycelium_field()

# Feature Extraction
compute_fractal_features()
estimate_fractal_dimension()
generate_fractal_ifs()
compute_nernst_potential()
```

### 5.3 Add Tests

Create `tests/examples/test_my_new_use_case.py`:

```python
def test_run_demo_no_exceptions():
    from my_new_use_case import run_demo
    run_demo(verbose=False)

def test_feature_ranges():
    from my_new_use_case import run_demo
    result = run_demo(verbose=False, return_result=True)
    assert result.some_metric >= 0
```

### 5.4 Update Documentation

1. Add entry to this document (MFN_USE_CASES.md)
2. Update README.md Examples & Use Cases section
3. Document any new public API usage patterns

### 5.5 Guidelines

- **Do NOT** modify core numerical engines
- **Do NOT** add heavy external dependencies
- **Do** use factory functions for configuration
- **Do** include sanity checks for feature ranges
- **Do** make tests fast (<5 seconds)

---

## 6. Feature Reference

All examples extract features from the 18-element FeatureVector defined in
[MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md):

| # | Feature | Category | Range |
|---|---------|----------|-------|
| 1 | `D_box` | Fractal | [0, 2.5] |
| 2 | `D_r2` | Fractal | [0, 1] |
| 3 | `V_min` | Basic Stats | [-95, 40] mV |
| 4 | `V_max` | Basic Stats | [-95, 40] mV |
| 5 | `V_mean` | Basic Stats | [-95, 40] mV |
| 6 | `V_std` | Basic Stats | [0, ∞) mV |
| 7 | `V_skew` | Basic Stats | (-∞, +∞) |
| 8 | `V_kurt` | Basic Stats | (-∞, +∞) |
| 9 | `dV_mean` | Temporal | [0, ∞) mV/step |
| 10 | `dV_max` | Temporal | [0, ∞) mV/step |
| 11 | `T_stable` | Temporal | [0, T] steps |
| 12 | `E_trend` | Temporal | (-∞, +∞) mV²/step |
| 13 | `f_active` | Structural | [0, 1] |
| 14 | `N_clusters_low` | Structural | [0, N²] |
| 15 | `N_clusters_med` | Structural | [0, N²] |
| 16 | `N_clusters_high` | Structural | [0, N²] |
| 17 | `max_cluster_size` | Structural | [0, N²] cells |
| 18 | `cluster_size_std` | Structural | [0, ∞) cells |

---

## 7. References

| Document | Description |
|----------|-------------|
| [MFN_SYSTEM_ROLE.md](MFN_SYSTEM_ROLE.md) | System capabilities and boundaries |
| [MFN_FEATURE_SCHEMA.md](MFN_FEATURE_SCHEMA.md) | Feature definitions and ranges |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture |
| [MFN_DATA_PIPELINES.md](MFN_DATA_PIPELINES.md) | Dataset generation pipelines |

---

*Document maintained by: MFN Development Team*  
*Last updated: 2025-11-30*
