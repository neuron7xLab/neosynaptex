# MLSDM Production Runbook

**Status**: See [status/READINESS.md](status/READINESS.md) (not yet verified)
**Last Updated**: December 2025
**Maintainer**: neuron7x

## Table of Contents

1. [Service Overview](#service-overview)
2. [Quick Reference](#quick-reference)
3. [Deployment](#deployment)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Common Issues](#common-issues)
6. [Troubleshooting](#troubleshooting)
7. [Incident Response](#incident-response)
8. [Maintenance](#maintenance)
9. [Disaster Recovery](#disaster-recovery)

---

## Service Overview

**Purpose**: Governed neurobiologically-grounded cognitive architecture with moral governance, phase-based memory, and cognitive rhythm (readiness tracked in [status/READINESS.md](status/READINESS.md)).

**Architecture**:
- FastAPI-based REST API
- In-memory cognitive engine
- Prometheus metrics export
- Health check endpoints

**Key Features**:
- Hard memory limit (20k vectors, ≤1.4 GB RAM)
- Adaptive moral homeostasis (EMA + dynamic threshold)
- Circadian rhythm (8 wake + 3 sleep cycles)
- Thread-safe concurrent processing (1000+ RPS)

---

## Quick Reference

### Critical Endpoints

```
Health Checks:
- GET /health/liveness    - Process alive check (always 200)
- GET /health/readiness   - Ready for traffic (200/503)
- GET /health/detailed    - Comprehensive status
- GET /health/metrics     - Prometheus metrics

API Endpoints:
- POST /event             - Process cognitive event
- GET /state              - Get system state
```

### Key Metrics

```
# Process metrics
process_event_latency_seconds     - Event processing latency
total_events_processed            - Total events counter
accepted_events_count             - Accepted events counter
moral_filter_threshold            - Current moral threshold

# System metrics
memory_usage_bytes                - Memory consumption
cpu_usage_percent                 - CPU utilization
```

### Environment Variables

```bash
# Required
API_KEY=<secret>                  # API authentication key
CONFIG_PATH=/path/to/config.yaml  # Configuration file path

# Optional
MLSDM_ENV=production              # Environment (dev/staging/production)
DISABLE_RATE_LIMIT=0              # Disable rate limiting (testing only)
LOG_LEVEL=INFO                    # Logging level
```

---

## Deployment

### Docker Deployment

```bash
# Build image
docker build -f Dockerfile.neuro-engine-service -t mlsdm:latest .

# Run container
docker run -d \
  --name mlsdm-api \
  -p 8000:8000 \
  -e API_KEY=your-secret-key \
  -e MLSDM_ENV=production \
  -v $(pwd)/config:/etc/mlsdm:ro \
  --restart unless-stopped \
  mlsdm:latest

# Check health
curl http://localhost:8000/health/liveness

# View logs
docker logs -f mlsdm-api
```

### Kubernetes Deployment

```bash
# Deploy to production
kubectl apply -f deploy/k8s/production-deployment.yaml

# Check deployment status
kubectl get deployments -n mlsdm-production
kubectl get pods -n mlsdm-production

# Check pod health
kubectl describe pod -n mlsdm-production -l app=mlsdm-api

# View logs
kubectl logs -n mlsdm-production -l app=mlsdm-api --tail=100 -f

# Port forward for local testing
kubectl port-forward -n mlsdm-production svc/mlsdm-api 8000:80
```

### Rolling Update

```bash
# Update image
kubectl set image deployment/mlsdm-api \
  mlsdm-api=ghcr.io/neuron7xLab/mlsdm-neuro-engine:1.0.1 \
  -n mlsdm-production

# Watch rollout
kubectl rollout status deployment/mlsdm-api -n mlsdm-production

# Rollback if needed
kubectl rollout undo deployment/mlsdm-api -n mlsdm-production
```

---

## Performance & SLO Validation

### Running Performance Tests

The system includes automated performance and resilience validation tests that verify SLO compliance.

**Run Locally**:
```bash
# Fast performance tests (<2 min)
pytest tests/perf/ -v -m "benchmark and not slow"

# Fast resilience tests (<2 min)
pytest tests/resilience/ -v -m "not slow"

# Full test suite (including slow tests)
pytest tests/perf/ tests/resilience/ -v
```

**CI/CD Integration**:
- **Automatic**: Runs on main branch and labeled PRs (`perf`, `resilience`)
- **Scheduled**: Nightly comprehensive validation at 2 AM UTC
- **Manual**: Trigger via GitHub Actions workflow dispatch

### SLO Targets

Based on `SLO_SPEC.md`:

| Metric | Target | CI Threshold |
|--------|--------|--------------|
| **API P95 Latency** | < 120ms | < 150ms |
| **Engine P95 Latency** | < 500ms | < 600ms |
| **Error Rate** | < 0.5% | < 1.0% |
| **Availability** | ≥ 99.9% | ≥ 99.0% |

**Interpreting Results**:
- **Green** (within target): System meets SLO
- **Yellow** (within CI threshold): Acceptable for testing
- **Red** (exceeds CI threshold): Performance regression - investigate

### SLO Violation Response

**If P95 Latency Exceeds Target**:
1. Check system load and resource utilization
2. Review recent code changes for performance impact
3. Profile slow operations using metrics
4. Consider scaling horizontally or optimizing hot paths

**If Error Rate Exceeds Target**:
1. Check error logs for root cause
2. Verify LLM provider status
3. Review circuit breaker state
4. Check for configuration issues

**If Availability Drops**:
1. Check health endpoints immediately
2. Review recent deployments
3. Verify infrastructure (K8s, networking)
4. Execute incident response procedures

---

## Quick Diagnostic Reference

### Symptom → Action Table

Use this table for quick diagnosis and resolution of common issues.

| Symptom | Check / Command | Expected Result | Next Step / Escalation |
|---------|-----------------|-----------------|------------------------|
| **Readiness endpoint slow (P95 > 120ms)** | `pytest tests/perf/test_slo_api_endpoints.py::test_readiness_latency -v` | P95 < 120ms | Profile hot paths, check CPU usage, review recent code changes |
| **Memory usage growing** | `pytest tests/unit/test_cognitive_controller.py::TestCognitiveControllerMemoryLeak -v` | later_growth ≤ initial_growth × 2 | Check for unbounded caches, review event listener cleanup |
| **High error rate** | `curl http://localhost:8000/health/detailed` | `error_rate < 0.5%` | Check LLM backend status, review logs for exceptions |
| **Pod crashlooping** | `kubectl logs -n mlsdm-production -l app=mlsdm-api --tail=100` | No OOM errors, no panics | Check memory limits, review startup configuration |
| **SAST scan failing** | `bandit -r src/mlsdm --severity-level high --confidence-level high` | No HIGH/CRITICAL issues | Fix vulnerabilities or justify with `# nosec` |
| **Coverage gate failing** | `./coverage_gate.sh` | Coverage ≥ 75% | Add tests for uncovered code, verify test configuration |
| **Moral filter drifting** | `pytest tests/property/test_moral_filter_properties.py -v` | Threshold ∈ [0.30, 0.90] | Review toxic input patterns, check EMA parameters |
| **Deployment validation failing** | `./deploy/scripts/validate-manifests.sh` | All manifests valid | Fix YAML syntax, check resource limits, verify image tags |
| **Core implementation check failing** | `./scripts/verify_core_implementation.sh` | 0 TODOs in core modules | Remove or implement TODOs, verify test collection |
| **Policy validation failing** | `python scripts/validate_policy_config.py` | 0 errors | Fix policy file references, verify workflow paths |
| **Liveness endpoint failing** | `curl http://localhost:8000/health/liveness` | 200 OK | Check if process is alive, review OOM events |
| **High memory usage** | `curl http://localhost:8000/health/metrics \| grep memory_usage_bytes` | < 1400 MB | Trigger cleanup, check PELM capacity, review memory limits |
| **Circuit breaker open** | Check `mlsdm_circuit_breaker_state` metric | `state = 0` (closed) | Investigate upstream failures, check LLM provider |

### Script Reference

All operational scripts with their locations and usage:

| Script | Location | Purpose | Command |
|--------|----------|---------|---------|
| **Coverage Gate** | `./coverage_gate.sh` | Enforce 75% code coverage | `./coverage_gate.sh` |
| **Validate Manifests** | `./deploy/scripts/validate-manifests.sh` | Validate K8s YAML syntax | `./deploy/scripts/validate-manifests.sh [--strict]` |
| **Verify Core** | `./scripts/verify_core_implementation.sh` | Check core modules complete | `./scripts/verify_core_implementation.sh` |
| **Validate Policy** | `./scripts/validate_policy_config.py` | Verify policy consistency | `python scripts/validate_policy_config.py` |
| **Security Audit** | `./scripts/security_audit.py` | Manual security checks | `python scripts/security_audit.py` |
| **Test Security** | `./scripts/test_security_features.py` | Validate security features | `python scripts/test_security_features.py` |

### Test Commands for SLO Validation

| SLO | Test Command | Target | CI Threshold |
|-----|--------------|--------|--------------|
| **Readiness Latency** | `pytest tests/perf/test_slo_api_endpoints.py::test_readiness_latency -v` | P95 < 120ms | P95 < 150ms |
| **Memory Leak** | `pytest tests/unit/test_cognitive_controller.py::TestCognitiveControllerMemoryLeak -v` | growth ≤ 2× | growth ≤ 2× |
| **Moral Filter** | `pytest tests/property/test_moral_filter_properties.py -v` | [0.30, 0.90] | [0.30, 0.90] |
| **All Performance** | `pytest tests/perf/ -v -m "benchmark and not slow"` | All pass | < 2 min total |
| **All Resilience** | `pytest tests/resilience/ -v -m "not slow"` | All pass | < 2 min total |

---

## Monitoring & Alerts

### Health Checks

**Liveness Probe**:
- **Purpose**: Detect if process is alive
- **Endpoint**: `/health/liveness`
- **Expected**: 200 OK
- **Action**: Restart pod if failing

**Readiness Probe**:
- **Purpose**: Determine if ready for traffic
- **Endpoint**: `/health/readiness`
- **Expected**: 200 OK (ready), 503 (not ready)
- **Action**: Remove from load balancer if failing

**Checks Performed**:
- Memory manager initialized
- System memory < 95% used
- CPU usage < 98%

### Key Metrics to Monitor

```promql
# Request rate
rate(total_events_processed[5m])

# Error rate
rate(rejected_events_count[5m]) / rate(total_events_processed[5m])

# Latency (p95)
histogram_quantile(0.95, rate(process_event_latency_seconds_bucket[5m]))

# Memory usage
memory_usage_bytes / (1024^3)  # GB

# Moral threshold drift
delta(moral_filter_threshold[1h])
```

### Recommended Alerts

```yaml
# High error rate
- alert: HighRejectionRate
  expr: rate(rejected_events_count[5m]) / rate(total_events_processed[5m]) > 0.5
  for: 5m
  severity: warning

# High latency
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(process_event_latency_seconds_bucket[5m])) > 0.1
  for: 5m
  severity: warning

# Memory pressure
- alert: HighMemoryUsage
  expr: memory_usage_bytes > 1.8e9  # 1.8 GB
  for: 5m
  severity: critical

# Service down
- alert: ServiceDown
  expr: up{job="mlsdm-api"} == 0
  for: 1m
  severity: critical
```

---

## Common Issues

### Issue: High Rejection Rate

**Symptoms**:
- Many events rejected by moral filter
- `rejected_events_count` increasing rapidly

**Cause**:
- Moral threshold too high
- Input moral values consistently low

**Resolution**:
```bash
# Check current threshold
curl -H "Authorization: Bearer $API_KEY" \
  http://api/health/detailed | jq '.statistics.moral_filter_threshold'

# Monitor moral threshold
watch -n 5 'curl -s http://api/health/detailed | jq .statistics.moral_filter_threshold'

# Wait for adaptive adjustment (threshold will auto-adjust)
# If needed, restart service to reset threshold to initial value
```

### Issue: Memory Growth

**Symptoms**:
- Memory usage increasing beyond 1.4 GB
- OOM kills in Kubernetes

**Cause**:
- Memory leak (unlikely, system has hard limits)
- Configuration error (capacity too high)

**Resolution**:
```bash
# Check current memory state
curl http://api/health/detailed | jq '.memory_state'

# Verify configuration
kubectl get configmap mlsdm-config -n mlsdm-production -o yaml

# Check actual memory usage
kubectl top pods -n mlsdm-production

# If memory leak suspected, collect heap dump (if available)
# Otherwise, restart pod
kubectl delete pod -n mlsdm-production -l app=mlsdm-api --grace-period=30
```

### Issue: High Latency

**Symptoms**:
- P95 latency > 100ms
- Slow response times

**Cause**:
- High concurrent load
- Resource contention
- Sleep phase processing (intentionally slower)

**Resolution**:
```bash
# Check current phase
curl http://api/health/detailed | jq '.phase'

# If in sleep phase, latency is expected to be higher
# Otherwise, check CPU and memory
kubectl top pods -n mlsdm-production

# Check for resource throttling
kubectl describe pod -n mlsdm-production -l app=mlsdm-api

# Scale up if needed
kubectl scale deployment mlsdm-api --replicas=5 -n mlsdm-production
```

### Issue: Rate Limiting

**Symptoms**:
- Clients receiving 429 responses
- `rate_limit_exceeded` events in logs

**Cause**:
- Client exceeding 5 RPS limit
- Misconfigured rate limiter

**Resolution**:
```bash
# Check rate limiter configuration
curl http://api/health/detailed

# Review security logs for offending clients
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep rate_limit_exceeded

# Temporarily disable for specific client (not recommended)
# Or increase rate limit in configuration

# Long-term: implement per-tier rate limits
```

---

## Troubleshooting

### Debug Mode

```bash
# Enable debug logging
kubectl set env deployment/mlsdm-api LOG_LEVEL=DEBUG -n mlsdm-production

# View debug logs
kubectl logs -n mlsdm-production -l app=mlsdm-api --tail=100 -f | grep DEBUG

# Revert to INFO
kubectl set env deployment/mlsdm-api LOG_LEVEL=INFO -n mlsdm-production
```

### Pod Not Ready

```bash
# Check pod events
kubectl describe pod -n mlsdm-production <pod-name>

# Check readiness probe
kubectl logs -n mlsdm-production <pod-name> --previous

# Check health endpoint manually
kubectl port-forward -n mlsdm-production <pod-name> 8000:8000
curl http://localhost:8000/health/readiness
```

### Memory Manager Issues

```bash
# Check detailed health
curl http://api/health/detailed | jq .

# Look for error messages
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep ERROR

# Check memory layer norms
curl http://api/health/detailed | jq '.memory_state'
```

### Configuration Issues

```bash
# Validate configuration
kubectl get configmap mlsdm-config -n mlsdm-production -o yaml

# Test configuration locally
python -c "
from mlsdm.utils.config_loader import ConfigLoader
config = ConfigLoader.load_config('config/production-ready.yaml')
print('Configuration valid')
"

# Apply updated configuration
kubectl apply -f config/production-ready.yaml
kubectl rollout restart deployment/mlsdm-api -n mlsdm-production
```

---

## Deployment Rollback

### Automatic Rollback

The CI/CD pipeline includes automatic rollback on failed deployments. When smoke tests fail after deployment, the system automatically triggers a rollback to the previous version.

**Trigger Conditions:**
- Health endpoint returns non-200 status
- Readiness endpoint fails after 3 retries
- API generation test fails
- Memory subsystem check fails
- Metrics endpoint unavailable

**Rollback Process:**
1. Smoke tests run 2 minutes after deployment
2. If any test fails, rollback is triggered automatically
3. Previous container image is restored
4. Notification sent to monitoring channels
5. Rollback log uploaded as workflow artifact

### Manual Rollback

If you need to manually rollback a deployment:

#### Docker/Container Rollback

```bash
# 1. Identify current and previous versions
docker images ghcr.io/neuron7xLab/mlsdm-neuro-engine --format "{{.Tag}}" | head -5

# 2. Stop current container
docker stop mlsdm-api

# 3. Start previous version
docker run -d \
  --name mlsdm-api \
  -p 8000:8000 \
  -e API_KEY=$API_KEY \
  -e MLSDM_ENV=production \
  --restart unless-stopped \
  ghcr.io/neuron7xLab/mlsdm-neuro-engine:PREVIOUS_VERSION
```

#### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/mlsdm-api -n mlsdm-production

# Rollback to previous revision
kubectl rollout undo deployment/mlsdm-api -n mlsdm-production

# Rollback to specific revision
kubectl rollout undo deployment/mlsdm-api -n mlsdm-production --to-revision=3

# Monitor rollback progress
kubectl rollout status deployment/mlsdm-api -n mlsdm-production

# Verify rollback
kubectl get pods -n mlsdm-production
# Run basic health checks
curl https://api.production.example.com/health
curl https://api.production.example.com/health/ready
```

#### Git Tag Rollback

```bash
# 1. Identify the last working version
git tag --sort=-creatordate | head -10

# 2. Create new release from previous version
git checkout v1.2.0
git tag -a v1.2.0-hotfix -m "Rollback to v1.2.0 due to production issue"
git push origin v1.2.0-hotfix

# This will trigger the release workflow for the previous version
```

### Post-Rollback Actions

After a rollback, follow these steps:

1. **Verify System Health**
   ```bash
   # Run health checks
   curl https://api.production.example.com/health
   curl https://api.production.example.com/health/ready
   
   # Check metrics
   curl https://api.production.example.com/health/metrics
   
   # Monitor error rates
   # Check Grafana dashboards
   ```

2. **Document the Incident**
   - Create incident report in `docs/incidents/YYYY-MM-DD-incident.md`
   - Document root cause
   - List actions taken
   - Identify prevention measures

3. **Create Rollback Report**
   ```markdown
   # Rollback Report: v1.2.1 → v1.2.0
   
   **Date:** 2026-01-20
   **Trigger:** Automatic (smoke test failure)
   **Duration:** 5 minutes
   
   ## Issue
   - API generation endpoint timing out
   - Memory subsystem returning 500 errors
   
   ## Root Cause
   - Breaking change in memory consolidation logic
   - Missing backward compatibility check
   
   ## Resolution
   - Automatic rollback to v1.2.0
   - Smoke tests pass on rollback version
   
   ## Prevention
   - Add integration tests for memory consolidation
   - Enhance smoke tests to cover edge cases
   ```

4. **Fix and Re-deploy**
   - Fix the issue in development
   - Add tests to prevent regression
   - Test thoroughly in staging
   - Re-deploy with confidence

### Health Check Command Reference

```bash
# Run health check
curl http://api.example.com/health

# Run readiness check
curl http://api.example.com/health/ready

# Run Docker container smoke tests (for local validation)
make docker-smoke-neuro-engine

# Test API generation endpoint
curl -X POST http://api.example.com/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'
```

**Health Check Coverage:**
- Health/liveness endpoint
- Readiness endpoint
- API generation functionality
- Memory subsystem operational
- Metrics endpoint availability

**Expected Duration:** < 2 minutes

---

## Incident Response

### Severity Levels

**P0 - Critical**:
- Service completely down
- Data loss risk
- Security breach

**P1 - High**:
- Partial service degradation
- High error rate (>50%)
- Performance severely impacted

**P2 - Medium**:
- Minor service degradation
- Elevated error rate (>10%)
- Non-critical feature impaired

**P3 - Low**:
- Cosmetic issues
- Documentation updates needed

### Response Procedures

#### P0: Service Down

```bash
# 1. Check service status
kubectl get pods -n mlsdm-production

# 2. Check recent events
kubectl get events -n mlsdm-production --sort-by='.lastTimestamp'

# 3. Check logs
kubectl logs -n mlsdm-production -l app=mlsdm-api --tail=500

# 4. Quick restart if needed
kubectl rollout restart deployment/mlsdm-api -n mlsdm-production

# 5. If still down, rollback
kubectl rollout undo deployment/mlsdm-api -n mlsdm-production

# 6. Escalate if not resolved in 5 minutes
```

#### P1: High Error Rate

```bash
# 1. Identify error pattern
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep ERROR

# 2. Check metrics
curl http://api/health/metrics | grep error_count

# 3. Check if specific to certain clients
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep -A 5 "client_id"

# 4. Scale up if resource-related
kubectl scale deployment mlsdm-api --replicas=6 -n mlsdm-production

# 5. Monitor for improvement
watch kubectl get hpa -n mlsdm-production
```

---

## Maintenance

### Planned Maintenance

```bash
# 1. Announce maintenance window
# 2. Increase replicas for safety
kubectl scale deployment mlsdm-api --replicas=5 -n mlsdm-production

# 3. Perform updates
kubectl apply -f deploy/k8s/production-deployment.yaml

# 4. Monitor rollout
kubectl rollout status deployment/mlsdm-api -n mlsdm-production

# 5. Verify health
curl http://api/health/detailed

# 6. Return to normal replica count
kubectl scale deployment mlsdm-api --replicas=3 -n mlsdm-production
```

### Configuration Updates

```bash
# 1. Validate new configuration
python -c "
from mlsdm.utils.config_loader import ConfigLoader
config = ConfigLoader.load_config('config/production-ready.yaml')
print('Valid')
"

# 2. Update ConfigMap
kubectl create configmap mlsdm-config --from-file=config.yaml=config/production-ready.yaml \
  -n mlsdm-production --dry-run=client -o yaml | kubectl apply -f -

# 3. Rolling restart
kubectl rollout restart deployment/mlsdm-api -n mlsdm-production

# 4. Verify configuration loaded
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep "Configuration loaded"
```

### API Key Rotation

MLSDM supports automated API key rotation with zero downtime. The RBAC system allows
multiple API keys to be valid simultaneously during rotation.

**Environment Variable Method**:
```bash
# Step 1: Add new key alongside existing key
# Keys loaded from environment on startup:
# - API_KEY: Default write access key
# - ADMIN_API_KEY: Admin access key
# - API_KEY_n_VALUE, API_KEY_n_ROLES, API_KEY_n_USER: Numbered keys

# Step 2: Rolling restart to pick up new keys
kubectl rollout restart deployment/mlsdm-api -n mlsdm-production

# Step 3: Update clients to use new key

# Step 4: Remove old key and restart again
kubectl rollout restart deployment/mlsdm-api -n mlsdm-production
```

**Programmatic Rotation** (for dynamic key management):
```python
from mlsdm.security.rbac import get_role_validator, Role

validator = get_role_validator()

# Step 1: Add new key (multiple keys valid simultaneously)
validator.add_key(
    key="new-api-key-value",
    roles=[Role.WRITE],
    user_id="service-account-1",
    expires_at=time.time() + 86400 * 90,  # 90 days
    description="Rotation 2025-01"
)

# Step 2: Update clients to use new key

# Step 3: Remove old key
validator.remove_key("old-api-key-value")

# Verify key count
print(f"Active API keys: {validator.get_key_count()}")
```

**Key Expiration Monitoring**:
- Keys with `expires_at` set will be rejected after expiration
- Monitor logs for "Expired API key used" warnings
- Set up alerts for keys expiring within 7 days

**Rotation Best Practices**:
1. Rotate API keys every 90 days (recommended)
2. Always add new key before removing old key
3. Allow 24-48 hours overlap for client migration
4. Log all key operations for audit trail
5. Monitor for failed auth attempts during rotation

---

### Security Updates

```bash
# 1. Update base image
docker build -f Dockerfile.neuro-engine-service -t mlsdm:1.0.1 .

# 2. Scan for vulnerabilities
docker scan mlsdm:1.0.1

# 3. Push to registry
docker tag mlsdm:1.0.1 ghcr.io/neuron7xLab/mlsdm-neuro-engine:1.0.1
docker push ghcr.io/neuron7xLab/mlsdm-neuro-engine:1.0.1

# 4. Update deployment
kubectl set image deployment/mlsdm-api \
  mlsdm-api=ghcr.io/neuron7xLab/mlsdm-neuro-engine:1.0.1 \
  -n mlsdm-production

# 5. Monitor rollout
kubectl rollout status deployment/mlsdm-api -n mlsdm-production
```

---

## Disaster Recovery

### Backup Procedures

**Configuration**:
```bash
# Backup ConfigMaps and Secrets
kubectl get configmap mlsdm-config -n mlsdm-production -o yaml > backup/config-$(date +%Y%m%d).yaml
kubectl get secret mlsdm-secrets -n mlsdm-production -o yaml > backup/secrets-$(date +%Y%m%d).yaml
```

**Note**: This system uses in-memory storage. No persistent data to backup. State is ephemeral by design.

### Recovery Procedures

**Complete Cluster Failure**:
```bash
# 1. Restore configuration
kubectl apply -f backup/config-latest.yaml
kubectl apply -f backup/secrets-latest.yaml

# 2. Deploy service
kubectl apply -f deploy/k8s/production-deployment.yaml

# 3. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=mlsdm-api -n mlsdm-production --timeout=300s

# 4. Verify health
curl http://api/health/detailed

# 5. Resume traffic
# Update DNS/load balancer as needed
```

**Single Pod Failure**:
- Kubernetes will automatically restart failed pods
- No manual intervention required
- Monitor rollout: `kubectl get pods -n mlsdm-production -w`

---

## Contact Information

**Primary Maintainer**: neuron7x (GitHub: @neuron7x)
**On-Call Rotation**: See `.github/CODEOWNERS` for current maintainers
**Escalation Path**:
1. Primary: Check GitHub Issues for similar problems
2. Secondary: Create issue with `[URGENT]` prefix at https://github.com/neuron7xLab/mlsdm/issues
3. Critical: Tag @neuron7x in issue for immediate attention

**Communication Channels**:
- **Issues**: https://github.com/neuron7xLab/mlsdm/issues
- **Discussions**: https://github.com/neuron7xLab/mlsdm/discussions
- **Documentation**: https://github.com/neuron7xLab/mlsdm

---

## Alert-Specific Runbook Procedures

This section provides detailed procedures for each alert defined in `deploy/k8s/alerts/mlsdm-alerts.yaml`.

### HighErrorRate / HighErrorRateCritical

**Condition**: Error rate > 0.5% (warning) or > 1% (critical) for 5 minutes

**Possible Causes**:
- LLM backend failures
- Memory pressure causing emergency shutdown
- Configuration errors after deployment
- Upstream service issues

**Diagnosis Steps**:
```bash
# 1. Check error breakdown
curl http://api/health/metrics | grep mlsdm_errors_total

# 2. Check emergency shutdown status
curl http://api/health/detailed | jq '.emergency_shutdown'

# 3. Review recent logs for error patterns
kubectl logs -n mlsdm-production -l app=mlsdm-api --tail=200 | grep ERROR

# 4. Check LLM backend health
curl http://api/health/metrics | grep mlsdm_llm_failures_total
```

**Mitigation Steps**:
1. If LLM failures: Check LLM backend health, consider fallback
2. If memory pressure: Scale up or restart pods
3. If config error: Rollback deployment
4. If upstream issue: Escalate to upstream team

### HighLatency / HighLatencyCritical

**Condition**: P95 latency > 120ms (warning) or > 500ms (critical)

**Possible Causes**:
- LLM backend slow responses
- High concurrent load
- Resource contention (CPU/memory)
- Sleep phase processing (expected to be slower)

**Diagnosis Steps**:
```bash
# 1. Check current phase
curl http://api/health/detailed | jq '.phase'

# 2. Check LLM latency specifically
curl http://api/health/metrics | grep mlsdm_llm_request_latency

# 3. Check bulkhead queue depth
curl http://api/health/metrics | grep mlsdm_bulkhead

# 4. Check resource usage
kubectl top pods -n mlsdm-production
```

**Mitigation Steps**:
1. If in sleep phase: Latency increase is expected, wait for wake phase
2. If high load: Scale up replicas
3. If LLM slow: Consider timeout reduction or backend switch
4. If resource contention: Increase resource limits

### EmergencyShutdownSpike / EmergencyShutdownActive

**Condition**: Multiple emergency shutdowns or currently in shutdown state

**Possible Causes**:
- Memory limit exceeded (1.4 GB threshold)
- Processing timeout
- Configuration validation failure
- Safety violation

**Diagnosis Steps**:
```bash
# 1. Check shutdown reason in logs
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep "EMERGENCY SHUTDOWN"

# 2. Check memory metrics
curl http://api/health/metrics | grep mlsdm_memory_usage_bytes

# 3. Check detailed health status
curl http://api/health/detailed | jq '.components'
```

**Mitigation Steps**:
1. If memory issue:
   - Restart pods: `kubectl rollout restart deployment/mlsdm-api -n mlsdm-production`
   - Check for memory leaks in recent changes
2. If timeout issue:
   - Check LLM backend health
   - Increase timeout if appropriate
3. If config error:
   - Rollback to previous configuration
   - Validate config before retry

### MoralFilterBlockSpike / MoralFilterBlockSpikeCritical

**Condition**: > 30% (warning) or > 50% (critical) of requests blocked

**Possible Causes**:
- Data drift (input distribution changed)
- Adversarial attack
- Threshold misconfiguration
- Training data issues

**Diagnosis Steps**:
```bash
# 1. Check current moral threshold
curl http://api/health/detailed | jq '.statistics.moral_filter_threshold'

# 2. Check block reasons
curl http://api/health/metrics | grep mlsdm_moral_rejections_total

# 3. Review recent blocked request patterns (check logs)
kubectl logs -n mlsdm-production -l app=mlsdm-api | grep "moral_precheck"
```

**Mitigation Steps**:
1. If adversarial attack: Enable rate limiting, block suspicious IPs
2. If data drift: Review input sources, consider threshold adjustment
3. If threshold misconfiguration: Adjust moral_threshold in config
4. Log all blocked requests for analysis

### LLMTimeoutSpike / LLMTimeoutSpikeCritical

**Condition**: Multiple LLM timeout failures

**Possible Causes**:
- LLM backend overloaded
- Network issues to LLM provider
- LLM provider outage
- Request complexity too high

**Diagnosis Steps**:
```bash
# 1. Check LLM failure breakdown
curl http://api/health/metrics | grep mlsdm_llm_failures_total

# 2. Check LLM latency histogram
curl http://api/health/metrics | grep mlsdm_llm_request_latency

# 3. Test LLM backend directly if possible
# (depends on LLM provider)
```

**Mitigation Steps**:
1. Check LLM provider status page
2. Consider increasing timeout temporarily
3. Enable fallback LLM if configured
4. Reduce max_tokens to speed up responses
5. Scale up if using local LLM

### BulkheadSaturation / BulkheadRejectionsHigh

**Condition**: Bulkhead queue > 80 or high rejection rate

**Possible Causes**:
- Traffic spike
- Slow request processing
- Insufficient capacity
- Upstream retry storm

**Diagnosis Steps**:
```bash
# 1. Check bulkhead metrics
curl http://api/health/metrics | grep mlsdm_bulkhead

# 2. Check request rate
curl http://api/health/metrics | grep mlsdm_http_requests_total

# 3. Check active request latency
curl http://api/health/metrics | grep mlsdm_request_latency
```

**Mitigation Steps**:
1. Scale up replicas: `kubectl scale deployment mlsdm-api --replicas=5`
2. Increase bulkhead capacity (MLSDM_MAX_CONCURRENT)
3. Enable request prioritization for critical paths
4. Investigate source of traffic spike

### HighMemoryUsage / MemoryLimitExceeded

**Condition**: Memory > 45MB (warning) or > 50MB (critical)

**Possible Causes**:
- Memory leak (unlikely with hard limits)
- Configuration error (capacity too high)
- Large vector allocations

**Diagnosis Steps**:
```bash
# 1. Check memory state
curl http://api/health/detailed | jq '.memory_state'

# 2. Check memory metrics
curl http://api/health/metrics | grep mlsdm_memory

# 3. Check actual pod memory
kubectl top pods -n mlsdm-production
```

**Mitigation Steps**:
1. If near limit: Restart pod for clean slate
2. If config issue: Reduce memory capacity in config
3. If leak suspected: Capture heap dump, investigate recent changes

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11 | Initial production runbook | neuron7x |
| 1.1.0 | 2025-12 | Added alert-specific runbook procedures | copilot |

---

**Remember**: This is a cognitive architecture with adaptive behavior. Some variations in metrics are expected and healthy!
