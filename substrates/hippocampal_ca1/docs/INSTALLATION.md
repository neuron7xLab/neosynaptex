# Installation Guide

Complete installation instructions for all platforms.

## System Requirements

### Minimum

- **OS**: Linux, macOS, Windows 10+
- **Python**: 3.8 or higher
- **RAM**: 4 GB
- **Disk**: 500 MB

### Recommended

- **OS**: Ubuntu 22.04 LTS or macOS 13+
- **Python**: 3.10+
- **RAM**: 16 GB (for large simulations)
- **Disk**: 2 GB

## Quick Install

### Linux/macOS

```bash
# Clone repository
git clone https://github.com/neuron7xLab/Hippocampal-CA1-LAM.git
cd Hippocampal-CA1-LAM

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python test_golden_standalone.py
```

### Windows

```powershell
# Clone repository
git clone https://github.com/neuron7xLab/Hippocampal-CA1-LAM.git
cd Hippocampal-CA1-LAM

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python test_golden_standalone.py
```

## From PyPI (when published)

```bash
pip install Hippocampal-CA1-LAM
```

## Development Installation

For contributors:

```bash
# Clone your fork
git clone https://github.com/YOURUSERNAME/Hippocampal-CA1-LAM.git
cd Hippocampal-CA1-LAM

# Create development environment
python3 -m venv venv-dev
source venv-dev/bin/activate

# Install in editable mode with dev dependencies
pip install -e .
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Verify
python test_golden_standalone.py
pytest tests/ -v
```

## Dependencies

### Core Dependencies

```
numpy>=1.24.0
scipy>=1.10.0
scikit-learn>=1.2.0
```

### Development Dependencies

```
pytest>=7.4.0
pytest-cov>=4.1.0
flake8>=6.0.0
mypy>=1.5.0
black>=23.0.0
pre-commit>=3.3.0
```

### Optional Dependencies

```
matplotlib>=3.7.0  # For visualization examples
jupyter>=1.0.0     # For notebooks
```

## Platform-Specific Notes

### Ubuntu 22.04

```bash
# System dependencies (if needed)
sudo apt update
sudo apt install python3-dev python3-venv

# Continue with standard install
```

### macOS

```bash
# Install Python via Homebrew (if needed)
brew install python@3.10

# Continue with standard install
```

### Windows

- Install [Python from python.org](https://www.python.org/downloads/)
- Check "Add Python to PATH" during installation
- Use PowerShell or CMD for commands

## Docker Installation

```bash
# Build image
docker build -t Hippocampal-CA1-LAM .

# Run container
docker run -it Hippocampal-CA1-LAM python test_golden_standalone.py
```

Dockerfile:
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "test_golden_standalone.py"]
```

## Conda Installation

```bash
# Create conda environment
conda create -n ca1 python=3.10
conda activate ca1

# Install dependencies
conda install numpy scipy scikit-learn
pip install -r requirements.txt

# Verify
python test_golden_standalone.py
```

## Verification

After installation, verify everything works:

### 1. Golden Tests

```bash
python test_golden_standalone.py
```

Expected output:
```
✓ Network Stability
✓ Ca2+ Plasticity
✓ Input-Specific
✓ Theta-SWR
✓ Reproducibility

RESULTS: 5/5 PASSED
```

### 2. Import Test

```python
python -c "from data.biophysical_parameters import get_default_parameters; print('OK')"
```

### 3. Run Example

```bash
python examples/demo_unified_weights.py
```

## Troubleshooting

### Issue: ImportError

```
ModuleNotFoundError: No module named 'numpy'
```

**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Version Conflicts

```
ERROR: pip's dependency resolver...
```

**Solution**:
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Issue: Permission Denied (Linux/macOS)

```
PermissionError: [Errno 13] Permission denied
```

**Solution**:
```bash
# Don't use sudo with pip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: NumPy Fails to Build

**Solution**:
```bash
# Install pre-built wheels
pip install --upgrade pip wheel
pip install numpy scipy scikit-learn --only-binary :all:
```

## Updating

### From Git

```bash
git pull origin main
pip install -r requirements.txt --upgrade
python test_golden_standalone.py
```

### From PyPI

```bash
pip install --upgrade Hippocampal-CA1-LAM
```

## Uninstallation

```bash
# If installed via pip
pip uninstall Hippocampal-CA1-LAM

# If installed from source
cd Hippocampal-CA1-LAM
pip uninstall -r requirements.txt
cd ..
rm -rf Hippocampal-CA1-LAM
```

## Next Steps

After successful installation:

1. Read [Quick Start](../README.md#quick-start)
2. Try [Examples](../examples/)
3. Read [API Documentation](API.md)
4. Run [Tests](TESTING.md)

---

**Last updated**: December 14, 2025
