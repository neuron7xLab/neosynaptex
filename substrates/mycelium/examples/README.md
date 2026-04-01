# Examples

## Quick Start

```bash
# Install MFN + visualization dependencies
pip install -e "..[dev]"
pip install matplotlib notebook

# Run the quickstart notebook
jupyter notebook quickstart.ipynb
```

## Available Examples

| Example | Description |
|---------|-------------|
| [`quickstart.ipynb`](quickstart.ipynb) | Interactive notebook: simulate three regimes, detect anomalies, visualize fields, validate causally |
| [`quickstart.py`](quickstart.py) | Minimal Python script demonstrating the core pipeline |
| [`simple_simulation.py`](simple_simulation.py) | Step-by-step simulation with parameter exploration |
| [`visualize_field_evolution.py`](visualize_field_evolution.py) | Temporal field evolution visualization with matplotlib |
| [`finance_regime_detection.py`](finance_regime_detection.py) | Regime detection applied to financial time series patterns |
| [`rl_exploration.py`](rl_exploration.py) | Reinforcement learning exploration of simulation parameter space |

## Dependencies

The examples require `matplotlib` and `notebook` in addition to the core MFN package. These are not included in the `[dev]` extras to keep the core installation lightweight.

```bash
pip install matplotlib notebook
```
