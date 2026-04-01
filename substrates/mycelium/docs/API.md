# API Reference

## Overview

MyceliumFractalNet exposes a REST API via FastAPI. The API provides the same six canonical operations as the SDK, with identical semantics.

**Start the server:**

```bash
mfn api --host 0.0.0.0 --port 8000
```

**OpenAPI schema:** [`docs/contracts/openapi.v2.json`](contracts/openapi.v2.json)

**Contract verification:**

```bash
python scripts/export_openapi.py        # Export current schema
python scripts/check_openapi_contract.py # Verify against baseline
```

---

## Endpoints

### Health & Monitoring

#### `GET /health`

Returns engine status and version.

```json
{
  "status": "healthy",
  "engine_version": "0.1.0",
  "api_version": "v1",
  "uptime_seconds": 42.5
}
```

#### `GET /metrics`

Prometheus-format metrics: request counters per operation, latency histograms.

---

### Pipeline Operations

All pipeline endpoints accept JSON request bodies and return JSON responses.

#### `POST /v1/simulate`

Run a reaction-diffusion simulation.

**Request:**

```json
{
  "grid_size": 64,
  "steps": 32,
  "seed": 42,
  "alpha": 0.18,
  "turing_enabled": true,
  "quantum_jitter": true,
  "neuromodulation": {
    "profile": "gabaa_tonic_muscimol_alpha1beta3",
    "enabled": true,
    "dt_seconds": 1.0,
    "gabaa_tonic": {
      "agonist_concentration_um": 0.5,
      "shunt_strength": 0.3,
      "rest_offset_mv": 0.0
    },
    "serotonergic": null,
    "observation_noise": null
  }
}
```

The `neuromodulation` field is optional. Omitting it is equivalent to baseline mode.

**Response:**

```json
{
  "grid_size": 64,
  "steps": 32,
  "seed": 42,
  "field_min_v": -71.0,
  "field_max_v": -3.6,
  "field_mean_v": -50.2,
  "config_fingerprint": "a1b2c3d4..."
}
```

#### `POST /v1/extract`

Extract morphology descriptor from a simulation.

**Request:** Same as `/v1/simulate`.

**Response:** `MorphologyDescriptor` with 57-dimensional feature vector across 7 groups (fractal, stability, complexity, connectivity, temporal, cluster, spatial).

#### `POST /v1/detect`

Anomaly detection with regime classification.

**Request:** Same as `/v1/simulate`.

**Response:**

```json
{
  "label": "nominal",
  "score": 0.184,
  "confidence": 0.79,
  "regime": "stable",
  "regime_score": 0.65,
  "contributing_features": ["dynamic_threshold", "instability_index"],
  "evidence": { ... }
}
```

#### `POST /v1/forecast`

Forecast field evolution.

**Request:** Simulation spec + `horizon` parameter.

**Response:**

```json
{
  "horizon": 4,
  "version": "mfn-forecast-result-v1",
  "method": "adaptive_descriptor_extrapolation",
  "predicted_states": ["..."],
  "uncertainty_envelope": { "plasticity_index": 0.0, "..." : "..." },
  "benchmark_metrics": {
    "forecast_structural_error": 0.0005,
    "adaptive_damping": 0.85
  }
}
```

#### `POST /v1/compare`

Compare two field states.

**Request:** Two simulation specs (`spec_a`, `spec_b`).

**Response:**

```json
{
  "label": "near-identical",
  "distance": 0.0012,
  "cosine_similarity": 0.9998,
  "topology_drift": "stable"
}
```

#### `POST /v1/report`

Full pipeline with causal validation and artifact generation.

**Request:** Simulation spec + output configuration.

**Response:** `ArtifactManifest` with paths to generated JSON, HTML, causal validation results, and Ed25519 signatures.

---

## Authentication

API key authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/v1/simulate -d '{...}'
```

Configuration: Set `MFN_API_KEY` environment variable or configure in `configs/prod.json`.

---

## Security

| Measure | Implementation |
|---------|---------------|
| Authentication | API key via `X-API-Key` header |
| Rate limiting | Configurable per-endpoint limits |
| CORS | Configurable origin allowlist |
| Headers | CSP, HSTS, X-Content-Type-Options, X-Frame-Options |
| Request limits | Maximum body size enforced |
| Output sanitization | Error messages scrubbed of internal paths |
| Input validation | SQL injection, XSS, and path traversal pattern detection |

---

## Error Responses

All errors return structured JSON:

```json
{
  "detail": "Grid size must be between 4 and 1024",
  "error_type": "validation_error",
  "status_code": 422
}
```

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request (malformed JSON) |
| 401 | Unauthorized (missing or invalid API key) |
| 422 | Validation error (invalid parameters) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Semantic Parity

The SDK is the semantic source of truth. CLI and API are orchestration layers over the same engine functions:

```
SDK:  mfn.simulate(spec)           <-- canonical implementation
CLI:  mfn simulate --seed 42       <-- calls SDK
API:  POST /v1/simulate {seed: 42} <-- calls SDK
```

Given identical inputs, all three surfaces produce identical outputs.

---

## Neuromodulation Surface

All `/v1/*` simulation endpoints accept a nested `neuromodulation` object. The schema is documented in the OpenAPI v2 contract.

**Backward compatibility:** Omitting the `neuromodulation` field produces results identical to v4.0.0 baseline behavior. No existing client code needs modification.

**Available profiles:**

| Profile | Description |
|---------|-------------|
| `baseline_nominal` | No modulation (control condition) |
| `gabaa_tonic_muscimol_alpha1beta3` | GABA-A tonic inhibition |
| `gabaa_tonic_extrasynaptic_delta_high_affinity` | Extrasynaptic GABA-A |
| `serotonergic_reorganization_candidate` | Serotonergic plasticity |
| `balanced_criticality_candidate` | Near-critical dynamics |
| `observation_noise_gaussian_temporal` | Gaussian temporal smoothing noise model |
