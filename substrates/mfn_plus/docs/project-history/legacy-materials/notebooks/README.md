# MyceliumFractalNet Jupyter Notebooks

Interactive notebooks for exploring and visualizing MyceliumFractalNet capabilities.

## Notebooks

| Notebook | Description | Runtime |
|:---------|:------------|:--------|
| [01_field_simulation.ipynb](01_field_simulation.ipynb) | Field simulation, Nernst potentials, animated evolution | ~2-3 min |
| [02_feature_analysis.ipynb](02_feature_analysis.ipynb) | Feature extraction, PCA, correlation analysis | ~3-5 min |
| [03_fractal_exploration.ipynb](03_fractal_exploration.ipynb) | Fractal dimension, box-counting, pattern complexity | ~3-5 min |

## Quick Start

### Local Installation

```bash
# Install MyceliumFractalNet with dev dependencies
pip install -e ".[dev]"

# Install Jupyter
pip install jupyter matplotlib seaborn scikit-learn

# Launch Jupyter
jupyter notebook notebooks/
```

### Google Colab

Click on any notebook above and use the "Open in Colab" button, or:

1. Go to [Google Colab](https://colab.research.google.com/)
2. Select "GitHub" tab
3. Enter: `neuron7x/mycelium-fractal-net`
4. Choose a notebook from the `notebooks/` directory

The notebooks include automatic package installation for Colab environments.

## Requirements

- Python ≥ 3.10
- mycelium-fractal-net
- matplotlib
- numpy
- pandas
- seaborn (for feature analysis)
- scikit-learn (for PCA and ML examples)

## Learning Path

**Beginner**: Start with `01_field_simulation.ipynb` to understand basic concepts.

**Intermediate**: Continue to `02_feature_analysis.ipynb` to learn about feature extraction.

**Advanced**: Explore `03_fractal_exploration.ipynb` for deep dive into fractal analysis.

## Interactive Features

All notebooks include:
- ✓ Executable code cells
- ✓ Visualizations and animations
- ✓ Statistical analysis
- ✓ Parameter exploration
- ✓ Markdown explanations

## Tips

### Performance

- Use smaller grid sizes (32×32) for faster experimentation
- Reduce number of simulation steps for quick tests
- Sample frames when creating animations

### Visualization

- Adjust color maps with `cmap` parameter (e.g., 'viridis', 'plasma', 'coolwarm')
- Use `figsize=(width, height)` to control plot sizes
- Save figures with `plt.savefig('filename.png', dpi=300)`

### Troubleshooting

**Kernel crashes**: Reduce simulation size or number of iterations.

**Slow execution**: Close other notebooks and clear output cells.

**Import errors**: Run the first cell that installs dependencies.

**Memory issues**: Restart kernel and clear all outputs.

## Export Results

### Save Figures

```python
plt.savefig('figure.png', dpi=300, bbox_inches='tight')
```

### Export Data

```python
import pandas as pd
df.to_csv('features.csv', index=False)
df.to_parquet('features.parquet')
```

### Create Animation Files

```python
from matplotlib.animation import FuncAnimation, FFMpegWriter

anim = FuncAnimation(fig, update, frames=frames)
anim.save('evolution.mp4', writer='ffmpeg', fps=10)
```

## Further Reading

- [MFN Documentation](../docs/)
- [API Reference](../docs/MFN_CODE_STRUCTURE.md)
- [Feature Schema](../docs/MFN_FEATURE_SCHEMA.md)
- [Mathematical Model](../docs/MFN_MATH_MODEL.md)

## Contributing

Found an issue or have a suggestion? Please open an issue on GitHub.

---

**License**: MIT  
**Maintainer**: Yaroslav Vasylenko (@neuron7x)
