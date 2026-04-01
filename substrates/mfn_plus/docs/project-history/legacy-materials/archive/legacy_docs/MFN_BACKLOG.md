# MFN Backlog – Systematic Work Plan

**Document Version**: 1.1  
**Created**: 2025-11-29  
**Updated**: 2025-11-30  
**Target**: MyceliumFractalNet v4.1 → Production-Ready Component  
**Status**: Active

---

## Completed Items (P0)

The following P0 critical items have been implemented:

| ID | Title | Status | PR/Commit |
|----|-------|--------|-----------|
| MFN-API-001 | Implement API authentication middleware | ✅ DONE | copilot/add-production-guardrails |
| MFN-API-002 | Add rate limiting to REST API | ✅ DONE | copilot/add-production-guardrails |
| MFN-OBS-001 | Implement Prometheus metrics endpoint | ✅ DONE | copilot/add-production-guardrails |
| MFN-LOG-001 | Add structured JSON logging | ✅ DONE | copilot/add-production-guardrails |
| MFN-TEST-001 | Add API load/performance tests | ✅ DONE | copilot/add-production-guardrails |

**Implementation Details:**
- Authentication: `X-API-Key` header middleware, configurable via `MFN_API_KEY`/`MFN_API_KEY_REQUIRED`
- Rate Limiting: Token bucket algorithm, per-endpoint limits, configurable via `MFN_RATE_LIMIT_*`
- Metrics: `/metrics` endpoint with `mfn_http_requests_total`, `mfn_http_request_duration_seconds`, `mfn_http_requests_in_progress`
- Logging: JSON structured logs with `X-Request-ID` correlation, configurable via `MFN_LOG_*`
- Tests: Locust scenarios in `load_tests/locustfile.py`, pytest perf tests in `tests/performance/`

---

## Overview

This backlog consolidates all identified gaps from the following source documents:

- **TECHNICAL_AUDIT.md** — PARTIAL and MISSING implementation status across code, tests, infra, and docs
- **MFN_SYSTEM_ROLE.md** — Required capabilities for MFN's role as a fractal morphogenetic feature engine
- **MFN_INTEGRATION_GAPS.md** / **mfn_integration_gaps.yaml** — Integration layer readiness assessment (PARTIAL/MISSING)
- **ROADMAP.md** — Planned features and version milestones (v4.1 → v4.3)

**Goal**: Transform MFN from a `partial_implementation` (maturity 3.5/5) into a production-ready service component with proper observability, security, and integration capabilities.

---

## Summary Table (by Priority)

| ID | Title | Priority | Category | Layer ID | Type | Status |
|----|-------|----------|----------|----------|------|--------|
| MFN-API-001 | Implement API authentication middleware | P0 | external_api | mfn-auth | feature | ✅ DONE |
| MFN-API-002 | Add rate limiting to REST API | P0 | external_api | mfn-rate-limiting | feature | ✅ DONE |
| MFN-OBS-001 | Implement Prometheus metrics endpoint | P0 | monitoring_metrics | mfn-monitoring | feature | ✅ DONE |
| MFN-LOG-001 | Add structured JSON logging | P0 | logging_tracing | mfn-logging | feature | ✅ DONE |
| MFN-TEST-001 | Add API load/performance tests | P0 | tests | null | feature | ✅ DONE |
| MFN-TEST-002 | Configure pytest-cov with coverage badge in CI | P1 | tests | mfn-ci-cd | infra | |
| MFN-API-003 | Add CORS configuration to REST API | P1 | external_api | mfn-api-rest | feature | |
| MFN-API-004 | Add request validation logging | P1 | external_api | mfn-api-rest | feature | |
| MFN-API-005 | Standardize API error responses | P1 | external_api | mfn-api-rest | refactor | |
| MFN-K8S-001 | Add Kubernetes Secrets management | P1 | infra | mfn-k8s | infra | |
| MFN-K8S-002 | Configure Ingress controller | P1 | infra | mfn-k8s | infra | |
| MFN-K8S-003 | Add Network Policies | P1 | infra | mfn-k8s | infra | |
| MFN-K8S-004 | Add PodDisruptionBudget | P1 | infra | mfn-k8s | infra | |
| MFN-CFG-001 | Create environment-specific configs (dev/staging/prod) | P1 | infra | mfn-config-json | infra | |
| MFN-CFG-002 | Add runtime config validation | P1 | infra | mfn-config-json | feature | |
| MFN-LOG-002 | Add distributed tracing (OpenTelemetry) | P1 | logging_tracing | mfn-logging | feature | |
| MFN-OBS-002 | Add simulation-specific metrics (fractal_dimension, growth_events) | P1 | monitoring_metrics | mfn-monitoring | feature | |
| MFN-DOC-001 | Export OpenAPI spec and configure Swagger UI | P1 | docs | mfn-api-rest | docs | |
| MFN-DOC-002 | Create detailed usage tutorials | P2 | docs | null | docs | |
| MFN-DOC-003 | Create troubleshooting guide | P2 | docs | null | docs | ✅ DONE |
| MFN-DEMO-001 | Create Jupyter notebooks for MFN visualization | P2 | docs | null | docs | |
| MFN-DEMO-002 | Add interactive field evolution visualizations | P2 | docs | null | feature | |
| MFN-BENCH-001 | Integrate benchmarks into CI for regression testing | P2 | tests | mfn-ci-cd | infra | |
| MFN-BENCH-002 | Add historical benchmark comparison | P2 | tests | null | feature | |
| MFN-SEC-001 | Integrate secrets management (Vault/AWS SM) | P2 | infra | mfn-secrets-mgmt | infra | |
| MFN-INT-001 | Design upstream connector interface | P2 | integration_adapter | mfn-upstream-connector | research | |
| MFN-INT-002 | Design downstream event publisher interface | P2 | integration_adapter | mfn-downstream-publisher | research | |
| MFN-API-006 | Implement WebSocket support | P3 | external_api | mfn-api-websocket | feature | |
| MFN-API-007 | Implement streaming API (SSE) | P3 | external_api | mfn-api-streaming | feature | |
| MFN-API-008 | Implement gRPC endpoints | P3 | external_api | mfn-api-grpc | feature | |
| MFN-RISK-001 | Design risk signals adapter interface | P3 | integration_adapter | mfn-risk-signals | research | |
| MFN-EDGE-001 | Create edge deployment configurations | P3 | infra | mfn-edge-deploy | infra | |

---

## P0 – Critical

These issues block MFN's operation as a production service.

### MFN-API-001 – Implement API authentication middleware

**Category:** `external_api`  
**Layer ID:** `mfn-auth`  
**Type:** `feature`  
**Depends on:** None  

**Summary**  
Implement authentication middleware for the FastAPI REST API. The API is currently completely open with no access control, making it unsuitable for production deployment. This task adds API key validation as the minimum viable authentication mechanism.

**Motivation**  
Per MFN_SYSTEM_ROLE.md Section 2.2 item 7 and Section 6.4 Question 11, authentication is explicitly listed as a non-responsibility but is recognized as needed for production. TECHNICAL_AUDIT.md lists "Authentication/Authorization" as MISSING under code_integration gaps. The integration gaps document (mfn-auth) marks this as a critical gap for production deployment.

**Acceptance Criteria**
- API key validation middleware is implemented
- All endpoints except `/health` require valid API key in header (e.g., `X-API-Key`)
- Invalid/missing API key returns 401 Unauthorized with standard error response
- API keys can be configured via environment variable or config file
- Documentation updated with authentication requirements

**Test Coverage**
- Unit tests: API key validation logic
- Integration tests: Protected endpoint access with valid/invalid/missing keys
- E2E tests: Full request cycle with authentication

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `docs/MFN_SYSTEM_ROLE.md#Non-Responsibilities`
- `docs/MFN_INTEGRATION_GAPS.md#Missing - Authentication & Authorization`
- `planning/mfn_integration_gaps.yaml#mfn-auth`

---

### MFN-API-002 – Add rate limiting to REST API

**Category:** `external_api`  
**Layer ID:** `mfn-rate-limiting`  
**Type:** `feature`  
**Depends on:** `MFN-API-001`  

**Summary**  
Implement rate limiting middleware to prevent API abuse and ensure fair resource allocation. Rate limits should be configurable per endpoint and, when authentication is available, per client.

**Motivation**  
TECHNICAL_AUDIT.md lists "Rate limiting" as MISSING. The mfn-rate-limiting layer in integration gaps specifies required functionality including per-client limits, global limits, burst handling, and 429 responses. Without rate limiting, the API is vulnerable to denial-of-service attacks.

**Acceptance Criteria**
- Rate limiting middleware is implemented (e.g., using `slowapi` or similar)
- Default rate limits configured (e.g., 100 req/min for simulation, 1000 req/min for health)
- Rate limits configurable via environment/config
- 429 Too Many Requests returned when limits exceeded with Retry-After header
- Rate limit headers included in responses (X-RateLimit-Limit, X-RateLimit-Remaining)

**Test Coverage**
- Unit tests: Rate limit calculation logic
- Integration tests: Rate limit enforcement, 429 response handling
- Load tests: Verify rate limiting under sustained traffic

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `docs/MFN_INTEGRATION_GAPS.md#Missing - Rate Limiting`
- `planning/mfn_integration_gaps.yaml#mfn-rate-limiting`

---

### MFN-OBS-001 – Implement Prometheus metrics endpoint

**Category:** `monitoring_metrics`  
**Layer ID:** `mfn-monitoring`  
**Type:** `feature`  
**Depends on:** None  

**Summary**  
Add a `/metrics` endpoint exposing Prometheus-format metrics for runtime observability. Include standard HTTP metrics (latency histograms, request counters, error rates) as the baseline.

**Motivation**  
TECHNICAL_AUDIT.md lists "Prometheus metrics" as MISSING under infra. MFN_SYSTEM_ROLE.md Section 5.3 Gap Summary identifies "Observability" as a primary gap. The mfn-monitoring layer specifies required metrics including latency histograms, request counters, and error rate gauges. Without metrics, production operation lacks visibility.

**Acceptance Criteria**
- `/metrics` endpoint returns Prometheus-format metrics
- HTTP request latency histogram (per endpoint, per status code)
- HTTP request counter (per endpoint, per method)
- HTTP error rate gauge
- Active requests gauge
- Metrics library integrated (e.g., `prometheus-fastapi-instrumentator` or `starlette-prometheus`)

**Test Coverage**
- Unit tests: Metric collection logic
- Integration tests: `/metrics` endpoint returns valid Prometheus format
- E2E tests: Metrics update correctly during request processing

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `docs/MFN_SYSTEM_ROLE.md#Gap Summary`
- `docs/MFN_INTEGRATION_GAPS.md#Missing - Prometheus Metrics`
- `planning/mfn_integration_gaps.yaml#mfn-monitoring`

---

### MFN-LOG-001 – Add structured JSON logging

**Category:** `logging_tracing`  
**Layer ID:** `mfn-logging`  
**Type:** `feature`  
**Depends on:** None  

**Summary**  
Replace basic Python logging with structured JSON logging. All log entries should include timestamp, level, message, and contextual fields (request_id, endpoint, etc.) for production debugging and log aggregation.

**Motivation**  
TECHNICAL_AUDIT.md lists "structured logging" as MISSING. The mfn-logging layer specifies JSON-structured log output with log levels and correlation IDs. Structured logs are essential for production debugging and integration with log aggregation systems (ELK, Loki).

**Acceptance Criteria**
- JSON-structured log output configured for all components
- Log levels configurable (DEBUG, INFO, WARN, ERROR)
- Request correlation ID generated and included in all request-scoped logs
- Correlation ID returned in response headers (X-Request-ID)
- Log format compatible with common aggregators (ELK, Loki)

**Test Coverage**
- Unit tests: Log formatting, correlation ID generation
- Integration tests: Logs contain expected fields during request processing

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `docs/MFN_INTEGRATION_GAPS.md#Missing - Structured Logging & Tracing`
- `planning/mfn_integration_gaps.yaml#mfn-logging`

---

### MFN-TEST-001 – Add API load/performance tests

**Category:** `tests`  
**Layer ID:** `null`  
**Type:** `feature`  
**Depends on:** None  

**Summary**  
Create load and performance tests for the REST API using tools like locust or k6. Tests should verify API behavior under sustained load and establish performance baselines.

**Motivation**  
TECHNICAL_AUDIT.md lists "Load/Performance tests" as MISSING. The audit notes that load testing API was not executed due to lack of tooling. Performance baselines are needed to detect regressions and ensure SLA compliance.

**Acceptance Criteria**
- Load testing tool configured (locust, k6, or similar)
- Test scenarios for key endpoints: `/validate`, `/simulate`, `/nernst`
- Performance baselines documented (latency p50/p95/p99, throughput)
- Tests can be run locally and in CI
- Test report generated with metrics summary

**Test Coverage**
- Load tests: Sustained traffic simulation
- Stress tests: Identify breaking points
- Spike tests: Sudden traffic increase handling

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `docs/TECHNICAL_AUDIT.md#Limitations & Assumptions`

---

## P1 – Important

These issues are needed for stable production integration.

### MFN-TEST-002 – Configure pytest-cov with coverage badge in CI

**Category:** `tests`  
**Layer ID:** `mfn-ci-cd`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Add pytest-cov to the CI pipeline and configure coverage reporting with a badge in README. Coverage data should be uploaded to Codecov or similar service.

**Motivation**  
TECHNICAL_AUDIT.md lists "Coverage reporting" as MISSING. While 305+ tests exist with 100% pass rate, there is no visibility into code coverage percentage. Coverage metrics help identify untested code paths.

**Acceptance Criteria**
- pytest-cov added to test dependencies
- CI workflow runs tests with coverage collection
- Coverage report uploaded to Codecov (or similar)
- Coverage badge added to README.md
- Minimum coverage threshold configured (e.g., 80%)

**Test Coverage**
- CI validation: Coverage collection works across Python versions

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`

---

### MFN-API-003 – Add CORS configuration to REST API

**Category:** `external_api`  
**Layer ID:** `mfn-api-rest`  
**Type:** `feature`  
**Depends on:** None  

**Summary**  
Configure CORS (Cross-Origin Resource Sharing) middleware for the FastAPI application. Allow configurable origins for development and production environments.

**Motivation**  
TECHNICAL_AUDIT.md lists "CORS configuration" as a missing feature in the REST API (code_integration PARTIAL). CORS is required for browser-based clients to access the API.

**Acceptance Criteria**
- CORS middleware configured in FastAPI
- Allowed origins configurable via environment/config
- Development mode allows all origins
- Production mode restricts to specific domains
- Proper handling of preflight OPTIONS requests

**Test Coverage**
- Integration tests: CORS headers present in responses
- Tests for allowed/blocked origins

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`
- `api.py`
- `planning/mfn_integration_gaps.yaml#mfn-api-rest`

---

### MFN-API-004 – Add request validation logging

**Category:** `external_api`  
**Layer ID:** `mfn-api-rest`  
**Type:** `feature`  
**Depends on:** `MFN-LOG-001`  

**Summary**  
Add logging for API request validation, including input parameters, validation errors, and request metadata. This aids debugging and audit trails.

**Motivation**  
TECHNICAL_AUDIT.md lists "request validation logging" as missing in the REST API. The mfn-api-rest layer in integration gaps identifies this as a missing feature. Request logging is essential for debugging production issues.

**Acceptance Criteria**
- All incoming requests logged with method, path, client IP
- Request parameters logged (with sensitive data masking)
- Validation errors logged with details
- Logs include correlation ID from MFN-LOG-001
- Log level configurable (DEBUG for full request body, INFO for metadata only)

**Test Coverage**
- Unit tests: Log message formatting
- Integration tests: Logs generated for valid/invalid requests

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`
- `planning/mfn_integration_gaps.yaml#mfn-api-rest`

---

### MFN-API-005 – Standardize API error responses

**Category:** `external_api`  
**Layer ID:** `mfn-api-rest`  
**Type:** `refactor`  
**Depends on:** None  

**Summary**  
Implement standardized error response format across all API endpoints. Errors should include error code, message, details, and request ID for debugging.

**Motivation**  
The mfn-api-rest layer lists "Error handling standardization" as a missing feature. Consistent error responses improve client integration and debugging experience.

**Acceptance Criteria**
- Standard error response schema defined (code, message, details, request_id)
- Exception handlers registered for common errors (validation, auth, rate limit, internal)
- HTTP status codes correctly mapped to error types
- Error responses include correlation ID
- Documentation updated with error response format

**Test Coverage**
- Unit tests: Exception handler logic
- Integration tests: Error responses for various failure scenarios

**Source Refs**
- `api.py`
- `planning/mfn_integration_gaps.yaml#mfn-api-rest`

---

### MFN-K8S-001 – Add Kubernetes Secrets management

**Category:** `infra`  
**Layer ID:** `mfn-k8s`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Add Kubernetes Secret resources to k8s.yaml for sensitive configuration. Secrets should be referenced by the deployment for API keys, credentials, etc.

**Motivation**  
TECHNICAL_AUDIT.md classifies infra as PARTIAL, noting missing secrets management. The mfn-k8s layer lists "Secrets management" as a missing feature. Secrets should not be stored in ConfigMaps.

**Acceptance Criteria**
- Secret resource template added to k8s.yaml
- Deployment updated to mount secrets as environment variables
- Documentation for creating secrets in different environments
- Example secret values (placeholder) included

**Test Coverage**
- Manual verification: Kubernetes deployment with secrets

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`
- `k8s.yaml`
- `planning/mfn_integration_gaps.yaml#mfn-k8s`

---

### MFN-K8S-002 – Configure Ingress controller

**Category:** `infra`  
**Layer ID:** `mfn-k8s`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Add Ingress resource to k8s.yaml for external HTTP(S) access. Configure TLS termination and path-based routing.

**Motivation**  
The mfn-k8s layer lists "Ingress controller configuration" as missing. Currently only ClusterIP service is configured, requiring port-forwarding for external access.

**Acceptance Criteria**
- Ingress resource added to k8s.yaml
- TLS configuration with secret reference
- Annotations for common ingress controllers (nginx, traefik)
- Health check path configured
- Documentation for DNS and certificate setup

**Test Coverage**
- Manual verification: External access via Ingress

**Source Refs**
- `k8s.yaml`
- `planning/mfn_integration_gaps.yaml#mfn-k8s`

---

### MFN-K8S-003 – Add Network Policies

**Category:** `infra`  
**Layer ID:** `mfn-k8s`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Add NetworkPolicy resources to restrict pod-to-pod communication. MFN pods should only accept traffic from Ingress and monitoring namespaces.

**Motivation**  
The mfn-k8s layer lists "Network policies" as missing. Network policies are a security best practice for limiting blast radius in case of compromise.

**Acceptance Criteria**
- NetworkPolicy resource added to k8s.yaml
- Ingress traffic allowed from Ingress controller namespace
- Egress traffic allowed to monitoring namespace
- Default deny for other traffic
- Documentation for network policy requirements

**Test Coverage**
- Manual verification: Network policy enforcement in cluster

**Source Refs**
- `k8s.yaml`
- `planning/mfn_integration_gaps.yaml#mfn-k8s`

---

### MFN-K8S-004 – Add PodDisruptionBudget

**Category:** `infra`  
**Layer ID:** `mfn-k8s`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Add PodDisruptionBudget resource to ensure minimum availability during voluntary disruptions (upgrades, node drains).

**Motivation**  
The mfn-k8s layer lists "PodDisruptionBudget" as missing. PDB ensures high availability during cluster maintenance operations.

**Acceptance Criteria**
- PodDisruptionBudget resource added to k8s.yaml
- Minimum available pods configured (e.g., minAvailable: 2 or maxUnavailable: 1)
- Documentation for PDB configuration

**Test Coverage**
- Manual verification: PDB prevents simultaneous pod eviction

**Source Refs**
- `k8s.yaml`
- `planning/mfn_integration_gaps.yaml#mfn-k8s`

---

### MFN-CFG-001 – Create environment-specific configs (dev/staging/prod)

**Category:** `infra`  
**Layer ID:** `mfn-config-json`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Create environment-specific configuration files for development, staging, and production. Each environment should have appropriate settings for logging, resource limits, and feature flags.

**Motivation**  
TECHNICAL_AUDIT.md notes configs lack "environment-specific configs". The mfn-config-json layer lists this as missing. Different environments require different settings (e.g., debug logging in dev, optimized settings in prod).

**Acceptance Criteria**
- `configs/dev.json` created with development settings
- `configs/staging.json` created with staging settings
- `configs/prod.json` created with production settings
- Environment selection via MFN_ENV environment variable
- Documentation for environment configuration

**Test Coverage**
- Unit tests: Config loading per environment

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`
- `configs/`
- `planning/mfn_integration_gaps.yaml#mfn-config-json`

---

### MFN-CFG-002 – Add runtime config validation

**Category:** `infra`  
**Layer ID:** `mfn-config-json`  
**Type:** `feature`  
**Depends on:** None  

**Summary**  
Add runtime validation for configuration values using Pydantic or similar. Invalid configurations should fail fast with clear error messages.

**Motivation**  
The mfn-config-json layer lists "Config validation at runtime" as missing. Runtime validation prevents silent failures from misconfiguration.

**Acceptance Criteria**
- Configuration schema defined with Pydantic models
- Validation runs at startup before any processing
- Clear error messages for validation failures
- Required vs optional fields documented
- Default values specified in schema

**Test Coverage**
- Unit tests: Valid/invalid config scenarios
- Integration tests: Application fails fast on invalid config

**Source Refs**
- `planning/mfn_integration_gaps.yaml#mfn-config-json`

---

### MFN-LOG-002 – Add distributed tracing (OpenTelemetry)

**Category:** `logging_tracing`  
**Layer ID:** `mfn-logging`  
**Type:** `feature`  
**Depends on:** `MFN-LOG-001`  

**Summary**  
Integrate OpenTelemetry for distributed tracing. Create spans for key operations (API requests, simulation runs, aggregation) to enable end-to-end request tracing.

**Motivation**  
TECHNICAL_AUDIT.md lists "distributed tracing" as MISSING. The mfn-logging layer specifies OpenTelemetry integration and W3C Trace Context propagation. Tracing is essential for debugging latency issues in distributed systems.

**Acceptance Criteria**
- OpenTelemetry SDK integrated
- Automatic instrumentation for FastAPI
- Custom spans for simulation and aggregation operations
- Trace context propagation (W3C format)
- Exporters configured for Jaeger/Zipkin (configurable)

**Test Coverage**
- Integration tests: Trace context propagated through request lifecycle
- Manual verification: Traces visible in tracing backend

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `planning/mfn_integration_gaps.yaml#mfn-logging`

---

### MFN-OBS-002 – Add simulation-specific metrics (fractal_dimension, growth_events)

**Category:** `monitoring_metrics`  
**Layer ID:** `mfn-monitoring`  
**Type:** `feature`  
**Depends on:** `MFN-OBS-001`  

**Summary**  
Extend Prometheus metrics with MFN-specific metrics: fractal_dimension histogram, growth_events counter, simulation duration, Lyapunov exponent gauge.

**Motivation**  
The mfn-monitoring layer specifies simulation-specific metrics beyond standard HTTP metrics. These metrics provide insight into MFN's computational characteristics and can trigger alerts on anomalies.

**Acceptance Criteria**
- fractal_dimension histogram metric (bucket ranges 1.0-2.0)
- growth_events counter per simulation
- simulation_duration_seconds histogram
- lyapunov_exponent gauge
- Metrics labeled by simulation parameters (grid_size, steps)

**Test Coverage**
- Integration tests: Metrics recorded during simulation
- E2E tests: Metrics values match simulation results

**Source Refs**
- `planning/mfn_integration_gaps.yaml#mfn-monitoring`
- `docs/MFN_FEATURE_SCHEMA.md`

---

### MFN-DOC-001 – Export OpenAPI spec and configure Swagger UI

**Category:** `docs`  
**Layer ID:** `mfn-api-rest`  
**Type:** `docs`  
**Depends on:** None  

**Summary**  
Export OpenAPI specification as static JSON/YAML file and configure Swagger UI endpoint for interactive API documentation in non-production environments.

**Motivation**  
TECHNICAL_AUDIT.md lists "OpenAPI spec export, Swagger UI in production" as MISSING. The mfn-api-rest layer identifies this as a missing feature. OpenAPI spec enables client code generation and API documentation.

**Acceptance Criteria**
- OpenAPI spec exported to `docs/openapi.json` (or .yaml)
- Swagger UI enabled at `/docs` (FastAPI default)
- ReDoc enabled at `/redoc` (FastAPI default)
- Interactive docs disabled in production via config flag
- Spec version matches API version

**Test Coverage**
- Integration tests: `/docs` and `/redoc` endpoints accessible
- Validation: OpenAPI spec is valid

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `planning/mfn_integration_gaps.yaml#mfn-api-rest`

---

## P2 – Enhancements

These issues improve quality and developer experience.

### MFN-DOC-002 – Create detailed usage tutorials

**Category:** `docs`  
**Layer ID:** `null`  
**Type:** `docs`  
**Depends on:** None  
**Status:** ✅ DONE  

**Summary**  
Create step-by-step tutorials for common MFN use cases: basic simulation, feature extraction, federated learning setup, and API integration.

**Motivation**  
TECHNICAL_AUDIT.md notes README has "basic instructions" but lacks "detailed tutorials". Detailed tutorials lower the barrier for new users and reduce support burden.

**Acceptance Criteria**
- Tutorial: Getting started with MFN simulation (CLI)
- Tutorial: Extracting features for ML pipelines
- Tutorial: Setting up federated learning
- Tutorial: Integrating with the REST API
- All tutorials tested and verified to work

**Test Coverage**
- Manual verification: Tutorials execute without errors

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`
- `README.md`

---

### MFN-DOC-003 – Create troubleshooting guide

**Category:** `docs`  
**Layer ID:** `null`  
**Type:** `docs`  
**Depends on:** None  

**Summary**  
Create troubleshooting guide covering common issues: installation problems, configuration errors, API errors, performance issues, and debugging tips.

**Motivation**  
TECHNICAL_AUDIT.md notes missing "troubleshooting guide" in usage docs. A troubleshooting guide reduces support burden and helps users self-diagnose issues.

**Acceptance Criteria**
- Section: Installation troubleshooting
- Section: Configuration troubleshooting
- Section: API error troubleshooting
- Section: Performance troubleshooting
- FAQ section with common questions

**Test Coverage**
- Manual verification: Guide covers observed issues

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`

---

### MFN-DEMO-001 – Create Jupyter notebooks for MFN visualization

**Category:** `docs`  
**Layer ID:** `null`  
**Type:** `docs`  
**Depends on:** None  

**Summary**  
Create interactive Jupyter notebooks demonstrating MFN capabilities with visualizations. Notebooks should cover field simulation, feature analysis, and fractal pattern exploration.

**Motivation**  
TECHNICAL_AUDIT.md lists "Jupyter notebooks" as MISSING. ROADMAP.md v4.3 mentions "Jupyter notebooks with visualizations" as a research feature. Interactive notebooks are valuable for exploration and education.

**Acceptance Criteria**
- Notebook: Field simulation and visualization (`notebooks/01_field_simulation.ipynb`)
- Notebook: Feature extraction analysis (`notebooks/02_feature_analysis.ipynb`)
- Notebook: Fractal dimension exploration (`notebooks/03_fractal_exploration.ipynb`)
- All notebooks executable with current codebase
- Binder or Google Colab compatibility

**Test Coverage**
- CI job: Notebooks execute without errors (nbconvert --execute)

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `docs/ROADMAP.md#v4.3`

---

### MFN-DEMO-002 – Add interactive field evolution visualizations

**Category:** `docs`  
**Layer ID:** `null`  
**Type:** `feature`  
**Depends on:** `MFN-DEMO-001`  

**Summary**  
Add interactive visualizations showing field evolution over time. Use matplotlib animations or Plotly for interactive exploration of simulation dynamics.

**Motivation**  
TECHNICAL_AUDIT.md lists "Interactive visualizations" as MISSING under examples/demo. Visualizations help users understand MFN's behavior and validate results.

**Acceptance Criteria**
- Animated field evolution visualization (matplotlib animation or Plotly)
- Interactive parameter exploration (Plotly widgets or ipywidgets)
- Visualization of growth events on field
- Export capability (GIF, MP4)
- Documentation for using visualizations

**Test Coverage**
- Manual verification: Visualizations render correctly

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`

---

### MFN-BENCH-001 – Integrate benchmarks into CI for regression testing

**Category:** `tests`  
**Layer ID:** `mfn-ci-cd`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Integrate existing benchmark suite into CI pipeline to detect performance regressions. Benchmark results should be compared against baselines.

**Motivation**  
TECHNICAL_AUDIT.md notes benchmarks lack "CI integration for regression testing". The benchmark_core.py exists but isn't run automatically. CI integration prevents accidental performance degradation.

**Acceptance Criteria**
- CI job runs benchmarks on main branch
- Benchmark results stored as artifacts
- Performance thresholds defined (fail if > 20% regression)
- Results compared against baseline file
- Notification on performance regression

**Test Coverage**
- CI validation: Benchmark job completes successfully

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`
- `benchmarks/benchmark_core.py`

---

### MFN-BENCH-002 – Add historical benchmark comparison

**Category:** `tests`  
**Layer ID:** `null`  
**Type:** `feature`  
**Depends on:** `MFN-BENCH-001`  

**Summary**  
Add capability to compare benchmark results across commits/versions. Store historical results and generate trend reports.

**Motivation**  
TECHNICAL_AUDIT.md notes benchmarks lack "historical comparison". Historical tracking helps identify gradual performance changes and validate optimization efforts.

**Acceptance Criteria**
- Benchmark results stored with git commit hash
- Comparison tool for two commits
- Trend visualization (optional)
- Results stored in machine-readable format (JSON)
- Documentation for benchmark workflow

**Test Coverage**
- Manual verification: Historical comparison produces meaningful output

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#PARTIAL`

---

### MFN-SEC-001 – Integrate secrets management (Vault/AWS SM)

**Category:** `infra`  
**Layer ID:** `mfn-secrets-mgmt`  
**Type:** `infra`  
**Depends on:** `MFN-K8S-001`  

**Summary**  
Integrate with external secrets management system (HashiCorp Vault or AWS Secrets Manager) for secure credential storage and rotation.

**Motivation**  
TECHNICAL_AUDIT.md lists "Secrets management" with Vault/AWS SM integration as MISSING. The mfn-secrets-mgmt layer specifies required functionality including rotation handling and K8s Secret mounting.

**Acceptance Criteria**
- Integration with at least one secrets backend (Vault or AWS SM)
- Secrets injected via environment variables or mounted files
- Secret rotation handling (graceful reload)
- Documentation for secrets backend setup
- Example configuration for each supported backend

**Test Coverage**
- Manual verification: Secrets retrieved from external backend

**Source Refs**
- `docs/TECHNICAL_AUDIT.md#MISSING`
- `planning/mfn_integration_gaps.yaml#mfn-secrets-mgmt`

---

### MFN-INT-001 – Design upstream connector interface

**Category:** `integration_adapter`  
**Layer ID:** `mfn-upstream-connector`  
**Type:** `research`  
**Depends on:** None  

**Summary**  
Research and design the interface for upstream data connectors. Define how external systems (Parameter Configurator, Data Preprocessor, Orchestration Layer) will inject data into MFN.

**Motivation**  
MFN_SYSTEM_ROLE.md Section 3.1 lists all upstream systems as "(Planned)" with no implementation. The mfn-upstream-connector layer is MISSING. Design work is needed before implementation.

**Acceptance Criteria**
- Design document specifying connector interface
- Input schema definitions for each upstream system type
- Protocol options evaluated (REST callback, message queue, direct call)
- Sequence diagrams for data flow
- Decision on synchronous vs asynchronous operation

**Test Coverage**
- N/A (research task)

**Source Refs**
- `docs/MFN_SYSTEM_ROLE.md#Upstream Systems`
- `planning/mfn_integration_gaps.yaml#mfn-upstream-connector`

---

### MFN-INT-002 – Design downstream event publisher interface

**Category:** `integration_adapter`  
**Layer ID:** `mfn-downstream-publisher`  
**Type:** `research`  
**Depends on:** None  

**Summary**  
Research and design the interface for downstream event publishing. Define how MFN will emit feature vectors and signals to external systems.

**Motivation**  
MFN_SYSTEM_ROLE.md Section 3.2 lists downstream systems (ML Model, Risk Module, etc.) all as "(Planned)". MFN_SYSTEM_ROLE.md Questions 6, 7, 13 ask about push vs pull and protocol selection. Design work needed before implementation.

**Acceptance Criteria**
- Design document specifying publisher interface
- Event schema definitions (feature vectors, signals)
- Protocol options evaluated (Kafka, RabbitMQ, webhooks)
- Delivery guarantees specified (at-least-once, at-most-once)
- Decision on push vs pull for different event types

**Test Coverage**
- N/A (research task)

**Source Refs**
- `docs/MFN_SYSTEM_ROLE.md#Downstream Systems`
- `docs/MFN_SYSTEM_ROLE.md#Open Questions`
- `planning/mfn_integration_gaps.yaml#mfn-downstream-publisher`

---

## P3 – Nice-to-have

These issues are optimizations or future enhancements.

### MFN-API-006 – Implement WebSocket support

**Category:** `external_api`  
**Layer ID:** `mfn-api-websocket`  
**Type:** `feature`  
**Depends on:** `MFN-API-001`, `MFN-API-002`  

**Summary**  
Add WebSocket endpoint for real-time bidirectional communication. Clients can subscribe to simulation updates and receive incremental field data.

**Motivation**  
ROADMAP.md v4.3 plans "WebSocket support". The mfn-api-websocket layer is MISSING. WebSocket enables efficient real-time applications without polling.

**Acceptance Criteria**
- WebSocket endpoint at `/ws/simulate`
- Connection authentication (using API key from MFN-API-001)
- Heartbeat/keepalive mechanism
- Graceful disconnect handling
- Message schema documented

**Test Coverage**
- Integration tests: WebSocket connection lifecycle
- E2E tests: Real-time message delivery

**Source Refs**
- `docs/ROADMAP.md#v4.3`
- `planning/mfn_integration_gaps.yaml#mfn-api-websocket`

---

### MFN-API-007 – Implement streaming API (SSE)

**Category:** `external_api`  
**Layer ID:** `mfn-api-streaming`  
**Type:** `feature`  
**Depends on:** `MFN-API-001`, `MFN-API-002`  

**Summary**  
Add Server-Sent Events (SSE) endpoint for push-based simulation updates. Simpler than WebSocket for one-way streaming use cases.

**Motivation**  
ROADMAP.md v4.3 plans "Streaming API". The mfn-api-streaming layer is MISSING. SSE is simpler than WebSocket for server-to-client push scenarios.

**Acceptance Criteria**
- SSE endpoint at `/stream/simulate`
- Connection authentication
- Incremental field updates as events
- Backpressure handling
- Client reconnection support (Last-Event-ID)

**Test Coverage**
- Integration tests: SSE connection and event delivery
- E2E tests: Event stream correctness

**Source Refs**
- `docs/ROADMAP.md#v4.3`
- `planning/mfn_integration_gaps.yaml#mfn-api-streaming`

---

### MFN-API-008 – Implement gRPC endpoints

**Category:** `external_api`  
**Layer ID:** `mfn-api-grpc`  
**Type:** `feature`  
**Depends on:** `MFN-API-001`  

**Summary**  
Add gRPC interface for high-performance RPC communication. Particularly valuable for federated learning coordination with efficient binary protocol.

**Motivation**  
ROADMAP.md v4.3 plans "gRPC endpoints". MFN_SYSTEM_ROLE.md Question 13 asks about gRPC. The mfn-api-grpc layer is MISSING. gRPC offers better performance than REST for high-frequency calls.

**Acceptance Criteria**
- Proto definitions for all API methods
- Unary RPCs for validate, nernst
- Server streaming for simulate
- Bidirectional streaming for federated aggregation
- Client/server interceptors for auth

**Test Coverage**
- Integration tests: gRPC method calls
- E2E tests: Full RPC workflow

**Source Refs**
- `docs/ROADMAP.md#v4.3`
- `docs/MFN_SYSTEM_ROLE.md#Open Questions`
- `planning/mfn_integration_gaps.yaml#mfn-api-grpc`

---

### MFN-RISK-001 – Design risk signals adapter interface

**Category:** `integration_adapter`  
**Layer ID:** `mfn-risk-signals`  
**Type:** `research`  
**Depends on:** `MFN-INT-002`  

**Summary**  
Research whether MFN should have a dedicated risk signals channel or if risk analysis should be downstream responsibility. Clarify Question 8 from MFN_SYSTEM_ROLE.md.

**Motivation**  
MFN_SYSTEM_ROLE.md Question 8 asks: "Should risk-related signals (e.g., regime change indicators) be a separate MFN output channel or computed by a downstream module using MFN features?" This is unresolved.

**Acceptance Criteria**
- Analysis document answering Question 8
- Pros/cons of MFN vs downstream risk computation
- Recommendation with rationale
- If MFN-owned: Interface design for risk signals
- If downstream-owned: Documentation of risk-relevant features

**Test Coverage**
- N/A (research task)

**Source Refs**
- `docs/MFN_SYSTEM_ROLE.md#Open Questions`
- `planning/mfn_integration_gaps.yaml#mfn-risk-signals`

---

### MFN-EDGE-001 – Create edge deployment configurations

**Category:** `infra`  
**Layer ID:** `mfn-edge-deploy`  
**Type:** `infra`  
**Depends on:** None  

**Summary**  
Create optimized deployment configurations for edge/IoT scenarios with minimal resource footprint and offline operation support.

**Motivation**  
ROADMAP.md v4.3 plans "Edge deployment". The mfn-edge-deploy layer is MISSING. Edge deployment enables MFN use in resource-constrained environments.

**Acceptance Criteria**
- Minimal Docker image optimized for size
- ARM architecture support (ARM64)
- Offline operation mode (no external dependencies)
- Resource optimization documentation
- Example deployment for Raspberry Pi or similar

**Test Coverage**
- Manual verification: Edge deployment on target hardware

**Source Refs**
- `docs/ROADMAP.md#v4.3`
- `planning/mfn_integration_gaps.yaml#mfn-edge-deploy`

---

## Dependency Notes

### Dependency Graph (High-Level)

```
P0 Dependencies:
├── MFN-API-001 (auth) ← MFN-API-002 (rate limiting)
├── MFN-LOG-001 (logging) ← MFN-API-004 (request logging)
└── Independent: MFN-OBS-001, MFN-TEST-001

P1 Dependencies:
├── MFN-LOG-001 ← MFN-LOG-002 (tracing)
├── MFN-OBS-001 ← MFN-OBS-002 (simulation metrics)
└── Independent: MFN-K8S-*, MFN-CFG-*, MFN-TEST-002, MFN-DOC-001

P2 Dependencies:
├── MFN-K8S-001 ← MFN-SEC-001 (secrets)
├── MFN-DEMO-001 ← MFN-DEMO-002 (visualizations)
├── MFN-BENCH-001 ← MFN-BENCH-002 (historical)
└── Independent: MFN-DOC-*, MFN-INT-*

P3 Dependencies:
├── MFN-API-001 + MFN-API-002 ← MFN-API-006, MFN-API-007, MFN-API-008
├── MFN-INT-002 ← MFN-RISK-001
└── Independent: MFN-EDGE-001
```

### Recommended Execution Order

1. **Phase 1 (P0 - Critical)**: Execute in parallel where possible
   - Start: MFN-OBS-001, MFN-LOG-001, MFN-TEST-001 (independent)
   - Then: MFN-API-001 (auth, required for API protection)
   - Then: MFN-API-002 (rate limiting, depends on auth)

2. **Phase 2 (P1 - Important)**: After P0 completion
   - Parallel: All MFN-K8S-*, MFN-CFG-*, MFN-TEST-002, MFN-DOC-001
   - Sequential: MFN-LOG-002 (after MFN-LOG-001), MFN-OBS-002 (after MFN-OBS-001)
   - Sequential: MFN-API-003, MFN-API-004, MFN-API-005

3. **Phase 3 (P2 - Enhancements)**: After P1 completion
   - Parallel: MFN-DOC-002, MFN-DOC-003, MFN-INT-001, MFN-INT-002
   - Sequential: MFN-DEMO-001 then MFN-DEMO-002
   - Sequential: MFN-BENCH-001 then MFN-BENCH-002
   - After MFN-K8S-001: MFN-SEC-001

4. **Phase 4 (P3 - Nice-to-have)**: After P2 completion
   - After MFN-API-001+002: MFN-API-006, MFN-API-007, MFN-API-008
   - After MFN-INT-002: MFN-RISK-001
   - Independent: MFN-EDGE-001

---

*Document generated from: TECHNICAL_AUDIT.md, MFN_SYSTEM_ROLE.md, MFN_INTEGRATION_GAPS.md, mfn_integration_gaps.yaml, ROADMAP.md*  
*Last updated: 2025-11-29*
