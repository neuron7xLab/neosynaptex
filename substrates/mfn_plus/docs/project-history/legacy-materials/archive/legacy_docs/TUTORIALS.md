# MyceliumFractalNet Tutorials

Step-by-step guides for common use cases and workflows.

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Running Your First Simulation](#2-running-your-first-simulation)
3. [Extracting Features for ML](#3-extracting-features-for-ml)
4. [Setting Up the API Server](#4-setting-up-the-api-server)
5. [Federated Learning Setup](#5-federated-learning-setup)
6. [Generating Datasets](#6-generating-datasets)
7. [Production Deployment](#7-production-deployment)
8. [Custom Integration](#8-custom-integration)

---

## 1. Getting Started

### Installation

**Prerequisites:**
- Python 3.10 or higher
- pip package manager
- (Optional) Docker for containerized deployment

**Steps:**

```bash
# Clone the repository
git clone https://github.com/neuron7x/mycelium-fractal-net.git
cd mycelium-fractal-net

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
python -c "from mycelium_fractal_net import simulate_mycelium_field; print('✓ Installation successful')"
```

**Troubleshooting:**
- If torch installation is slow, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#problem-torch-installation-fails-or-is-slow)
- For dependency conflicts, create a fresh virtual environment

---

## 2. Running Your First Simulation

### CLI Usage

The simplest way to run MFN is through the command-line interface:

```bash
# Run a validation cycle
python mycelium_fractal_net_v4_1.py --mode validate --seed 42 --epochs 1

# Output:
# === MyceliumFractalNet v4.1 :: validation ===
# loss_start              :  2.432786
# loss_final              :  1.795847
# pot_min_mV              : -71.083952
# pot_max_mV              : -62.975776
# fractal_dimension       :  1.567234
# ...
```

### Python API

For more control, use the Python API:

```python
from mycelium_fractal_net import (
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
    compute_fractal_features,
)

# Create configuration
config = make_simulation_config_demo()
config.seed = 42
config.steps = 100

# Run simulation
result = run_mycelium_simulation_with_history(config)

# Access results
print(f"Final field shape: {result.field_final.shape}")
print(f"Growth events: {result.growth_events}")
print(f"Potential range: [{result.field_final.min():.1f}, {result.field_final.max():.1f}] mV")

# Extract features
features = compute_fractal_features(result)
print(f"Fractal dimension: {features['D_box']:.3f}")
```

### Configuration Options

MFN provides three preset configurations:

```python
from mycelium_fractal_net import make_simulation_config

# Small: 32×32 grid, 50 steps (~fast)
config_small = make_simulation_config("small")

# Medium: 64×64 grid, 100 steps (~moderate)
config_medium = make_simulation_config("medium")

# Large: 128×128 grid, 200 steps (~slow)
config_large = make_simulation_config("large")
```

---

## 3. Extracting Features for ML

MyceliumFractalNet extracts 18 standardized fractal features suitable for machine learning.

### Basic Feature Extraction

```python
from mycelium_fractal_net import (
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
    compute_fractal_features,
)

# Run simulation
config = make_simulation_config_demo()
result = run_mycelium_simulation_with_history(config)

# Extract all 18 features
features = compute_fractal_features(result)

# Features are organized by category:
# - Geometric: D_box, f_active, edge_density, cluster_coeff
# - Statistical: V_mean, V_std, V_skew, V_kurt, entropy, hurst
# - Temporal: dV_dt_mean, dV_dt_std, autocorr_lag1, persistence
# - Structural: gradient_mean, gradient_std, laplacian_mean, laplacian_std

print("Feature Vector:")
for key, value in features.items():
    print(f"  {key:20s}: {value:12.6f}")
```

### Creating Training Datasets

Generate multiple samples for ML training:

```python
import numpy as np
import pandas as pd

# Generate 100 samples with different seeds
samples = []
for seed in range(100):
    config = make_simulation_config_demo()
    config.seed = seed
    result = run_mycelium_simulation_with_history(config)
    features = compute_fractal_features(result)
    features['seed'] = seed  # Track seed
    samples.append(features)

# Convert to DataFrame
df = pd.DataFrame(samples)

# Save to parquet (efficient format)
df.to_parquet('mfn_features_100.parquet', index=False)

# Or CSV
df.to_csv('mfn_features_100.csv', index=False)

print(f"Generated {len(df)} feature vectors")
print(f"Shape: {df.shape}")
```

### Using with scikit-learn

```python
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier

# Load features
df = pd.read_parquet('mfn_features_100.parquet')

# Separate features from labels (if you have labels)
X = df.drop(['seed'], axis=1).values  # Feature matrix
# y = df['label'].values  # Your labels (if applicable)

# Standardize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Dimensionality reduction (optional)
pca = PCA(n_components=10)
X_pca = pca.fit_transform(X_scaled)

print(f"Original features: {X.shape[1]}")
print(f"Reduced features: {X_pca.shape[1]}")
print(f"Explained variance: {pca.explained_variance_ratio_.sum():.2%}")
```

---

## 4. Setting Up the API Server

MFN provides a FastAPI server for remote access.

### Basic Setup

```bash
# Start server on localhost
uvicorn api:app --host 0.0.0.0 --port 8000

# Server starts at: http://localhost:8000
# API docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

### Testing Endpoints

```bash
# Health check (public)
curl http://localhost:8000/health

# Run validation (requires auth in production)
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"seed": 42, "epochs": 1}'

# Simulate field
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"seed": 42, "grid_size": 64, "steps": 100, "turing_enabled": true}'

# Compute Nernst potential
curl -X POST http://localhost:8000/nernst \
  -H "Content-Type: application/json" \
  -d '{"z_valence": 1, "concentration_out_molar": 0.005, "concentration_in_molar": 0.14, "temperature_k": 310.0}'
```

### Production Configuration

Enable authentication and rate limiting:

```bash
# Set environment variables
export MFN_ENV=prod
export MFN_API_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
export MFN_API_KEY_REQUIRED=true
export MFN_RATE_LIMIT_ENABLED=true
export MFN_RATE_LIMIT_REQUESTS=100
export MFN_LOG_FORMAT=json

# Start server
uvicorn api:app --host 0.0.0.0 --port 8000

# Make authenticated request
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $MFN_API_KEY" \
  -d '{"seed": 42, "epochs": 1}'
```

### Using Python Client

```python
import httpx

# Create client
client = httpx.Client(base_url="http://localhost:8000")

# Health check
response = client.get("/health")
print(response.json())

# Run validation (with authentication)
api_key = "your-api-key"
response = client.post(
    "/validate",
    json={"seed": 42, "epochs": 1},
    headers={"X-API-Key": api_key}
)
result = response.json()
print(f"Fractal dimension: {result['example_fractal_dim']:.3f}")
```

---

## 5. Federated Learning Setup

MFN supports Byzantine-robust federated gradient aggregation.

### Single-Server Aggregation

```python
import numpy as np
from mycelium_fractal_net import aggregate_gradients_krum

# Simulate gradients from multiple clients
num_clients = 10
gradient_size = 100

# Generate synthetic gradients
gradients = []
for i in range(num_clients):
    gradient = np.random.randn(gradient_size).astype(np.float32)
    gradients.append(gradient)

# Add Byzantine (malicious) gradients
byzantine_ratio = 0.2
num_byzantine = int(num_clients * byzantine_ratio)
for i in range(num_byzantine):
    # Byzantine client sends large values
    gradients[i] = np.random.randn(gradient_size).astype(np.float32) * 10

# Aggregate using Krum (robust to Byzantine clients)
aggregated = aggregate_gradients_krum(
    gradients=gradients,
    num_clusters=10,
    byzantine_fraction=byzantine_ratio
)

print(f"Aggregated gradient shape: {aggregated.shape}")
print(f"Aggregated gradient norm: {np.linalg.norm(aggregated):.3f}")
```

### API-Based Aggregation

```python
import httpx

# Prepare gradients
gradients = [
    [0.1, 0.2, 0.3],  # Client 1
    [0.11, 0.19, 0.31],  # Client 2
    [0.09, 0.21, 0.29],  # Client 3
    [5.0, 5.0, 5.0],  # Byzantine client (outlier)
]

# Call API
client = httpx.Client(base_url="http://localhost:8000")
response = client.post(
    "/federated/aggregate",
    json={
        "gradients": gradients,
        "num_clusters": 4,
        "byzantine_fraction": 0.25
    },
    headers={"X-API-Key": "your-api-key"}
)

result = response.json()
print(f"Aggregated gradient: {result['aggregated_gradient']}")
```

---

## 6. Generating Datasets

Use the dataset generation pipeline for batch processing.

### Quick Dataset Generation

```bash
# Generate small test dataset (10 samples, <10 seconds)
python -m experiments.generate_dataset --preset small

# Generate medium dataset (100 samples, ~1-2 minutes)
python -m experiments.generate_dataset --preset medium

# Generate large production dataset (500 samples, ~10-20 minutes)
python -m experiments.generate_dataset --preset large

# Output saved to: data/scenarios/features_<preset>/<timestamp>/dataset.parquet
```

### Custom Dataset Generation

```python
from experiments.generate_dataset import generate_dataset, DatasetConfig

# Configure generation
config = DatasetConfig(
    num_samples=50,
    grid_sizes=[32, 64],
    steps_range=(50, 100),
    alpha_range=(0.1, 0.5),
    output_dir="data/custom_dataset"
)

# Generate
dataset_path = generate_dataset(config)
print(f"Dataset saved to: {dataset_path}")

# Load and inspect
import pandas as pd
df = pd.read_parquet(dataset_path)
print(df.describe())
```

### Analyzing Generated Data

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load dataset
df = pd.read_parquet('data/scenarios/features_medium/latest/dataset.parquet')

# Basic statistics
print(df.describe())

# Plot feature distributions
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
df['D_box'].hist(ax=axes[0,0], bins=20)
axes[0,0].set_title('Fractal Dimension')

df['V_mean'].hist(ax=axes[0,1], bins=20)
axes[0,1].set_title('Mean Potential')

df['entropy'].hist(ax=axes[1,0], bins=20)
axes[1,0].set_title('Entropy')

df['gradient_mean'].hist(ax=axes[1,1], bins=20)
axes[1,1].set_title('Mean Gradient')

plt.tight_layout()
plt.show()
```

---

## 7. Production Deployment

### Docker Deployment

```bash
# Build image
docker build -t mfn:4.1 .

# Run container
docker run -d \
  --name mfn-api \
  -p 8000:8000 \
  -e MFN_ENV=prod \
  -e MFN_API_KEY=your-secret-key \
  -e MFN_API_KEY_REQUIRED=true \
  mfn:4.1

# Check logs
docker logs mfn-api

# Test
curl http://localhost:8000/health
```

### Kubernetes Deployment

```bash
# Create namespace
kubectl apply -f k8s.yaml

# Create secret (replace with actual key)
kubectl create secret generic mfn-secrets \
  --from-literal=api-key=$(openssl rand -base64 32) \
  -n mycelium-fractal-net

# Verify deployment
kubectl get pods -n mycelium-fractal-net
kubectl get svc -n mycelium-fractal-net

# Port forward for testing
kubectl port-forward -n mycelium-fractal-net svc/mycelium-fractal-net 8000:80

# Test
curl http://localhost:8000/health

# View logs
kubectl logs -n mycelium-fractal-net -l app=mycelium-fractal-net
```

### Monitoring

```bash
# Check metrics endpoint (default: /metrics, configurable via MFN_METRICS_ENDPOINT)
curl http://localhost:8000/metrics

# Key metrics to monitor:
# - mfn_http_requests_total
# - mfn_http_request_duration_seconds
# - mfn_http_requests_in_progress

# Set up Prometheus scraping (if using Prometheus operator)
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mfn-metrics
  namespace: mycelium-fractal-net
spec:
  selector:
    matchLabels:
      app: mycelium-fractal-net
  endpoints:
    - port: http
      path: /metrics # update if MFN_METRICS_ENDPOINT is customized
EOF
```

---

## 8. Custom Integration

### Integrating MFN into Your Application

```python
# Your application code
from mycelium_fractal_net import (
    make_simulation_config,
    run_mycelium_simulation_with_history,
    compute_fractal_features,
)

class MyApplication:
    def __init__(self):
        # Initialize MFN configuration
        self.mfn_config = make_simulation_config("medium")
    
    def process_data(self, data):
        """Process input data and extract features."""
        # Adapt your data to MFN format
        self.mfn_config.seed = data.get('seed', 42)
        
        # Run simulation
        result = run_mycelium_simulation_with_history(self.mfn_config)
        
        # Extract features
        features = compute_fractal_features(result)
        
        # Use features in your pipeline
        return self.predict_with_features(features)
    
    def predict_with_features(self, features):
        """Your ML model prediction logic."""
        # Convert features dict to array
        feature_array = [features[k] for k in sorted(features.keys())]
        
        # Pass to your model
        # prediction = your_model.predict([feature_array])
        
        return feature_array

# Usage
app = MyApplication()
result = app.process_data({'seed': 123})
```

### Creating Custom Endpoints

```python
# custom_api.py
from fastapi import FastAPI
from mycelium_fractal_net import (
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
    compute_fractal_features,
)

app = FastAPI()

@app.post("/custom/analyze")
async def custom_analysis(params: dict):
    """Custom analysis endpoint."""
    config = make_simulation_config_demo()
    config.seed = params.get('seed', 42)
    
    # Run simulation
    result = run_mycelium_simulation_with_history(config)
    
    # Extract features
    features = compute_fractal_features(result)
    
    # Custom analysis logic
    complexity_score = features['D_box'] * features['entropy']
    
    return {
        "complexity_score": complexity_score,
        "fractal_dimension": features['D_box'],
        "entropy": features['entropy'],
        "features": features
    }
```

---

## Next Steps

- Explore [Jupyter notebooks](../notebooks/) for interactive tutorials
- Read [API documentation](MFN_CODE_STRUCTURE.md) for detailed API reference
- Check [Use Cases](MFN_USE_CASES.md) for real-world applications
- Review [Architecture](ARCHITECTURE.md) for system design

## Getting Help

- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [GitHub Issues](https://github.com/neuron7x/mycelium-fractal-net/issues)
- [Documentation](../docs/)

---

**Last Updated**: 2025-12-03  
**Version**: 4.1.0
