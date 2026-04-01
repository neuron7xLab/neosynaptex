# Contributing to CA1 Hippocampus Framework

Thank you for your interest in contributing!

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/neuron7xLab/Hippocampal-CA1-LAM/issues)
2. Create new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (OS, Python version)
   - Minimal reproducible example

### Suggesting Features

1. Check [existing issues](https://github.com/neuron7xLab/Hippocampal-CA1-LAM/issues)
2. Open feature request with:
   - Use case description
   - Proposed API
   - Scientific motivation (with DOI if applicable)

### Pull Requests

#### Setup

```bash
# Fork and clone
git clone https://github.com/neuron7xLab/Hippocampal-CA1-LAM.git
cd Hippocampal-CA1-LAM

# Create branch
git checkout -b feature/your-feature-name

# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

#### Development Process

1. **Write tests first** (TDD approach)
2. **Implement feature**
3. **Run golden tests**: `python test_golden_standalone.py`
4. **Check linting**: `flake8 . --max-line-length=100`
5. **Type check**: `mypy .`
6. **Update docs** if API changed

#### Code Standards

- **PEP 8**: Follow Python style guide
- **Type hints**: All functions must have type annotations
- **Docstrings**: Google-style format
- **No placeholders**: All code must be functional
- **Tests required**: Minimum 90% coverage

#### Example

```python
def my_function(param: float, flag: bool = True) -> np.ndarray:
    """
    Brief description.
    
    Detailed description with scientific context and DOI if applicable.
    
    Args:
        param: Description of param
        flag: Description of flag (default: True)
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param is negative
    
    Examples:
        >>> result = my_function(1.5)
        >>> print(result.shape)
        (10,)
    """
    if param < 0:
        raise ValueError("param must be non-negative")
    
    # Implementation
    return np.zeros(10)
```

#### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add CA3 recurrent connectivity
fix: correct spectral radius calculation
docs: update API reference for UnifiedWeightMatrix
test: add integration test for theta-SWR switching
perf: vectorize laminar EM e-step
```

#### Scientific Contributions

When adding neuroscience features:

1. **Provide DOI**: Link to primary experimental paper
2. **Extract parameters**: Show exact values from paper (figure/table)
3. **Add validation**: Create golden test with expected output
4. **Document assumptions**: Explain any simplifications

Example:

```python
# From Magee J Neurosci 1998 (DOI: 10.1523/JNEUROSCI.18-19-07613.1998)
# Figure 4: HCN conductance increases with depth
# Values extracted from patch-clamp recordings in CA1 pyramidal neurons
params.compartment.g_h = np.array([0.5, 1.5, 3.0, 5.0])  # mS/cm²
```

### Review Process

1. Automated checks run (CI/CD)
2. Maintainer reviews code
3. Request changes or approve
4. Merge to main

---

## Project Structure

```
hippocampal_ca1_lam/
├── data/                  # Parameters
├── core/                  # Core models
├── plasticity/            # Synaptic plasticity
├── ai_integration/        # LLM integration
├── validation/            # Tests and validators
├── docs/                  # Documentation
├── examples/              # Usage examples
└── tests/                 # Unit/integration tests
```

## Questions?

- Open an [Issue](https://github.com/neuron7xLab/Hippocampal-CA1-LAM/issues)

Thank you for contributing! 🧠
