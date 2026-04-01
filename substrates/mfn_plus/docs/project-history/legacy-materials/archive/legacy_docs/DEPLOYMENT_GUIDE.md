# Deployment Guide — MyceliumFractalNet v4.1

This guide hardens the FastAPI service for production Kubernetes clusters and explains how to wire secrets, configuration, scaling, and observability. The manifests live in `k8s.yaml` and are designed to run with restricted Pod Security, Prometheus scraping, and ingress TLS termination.

## Prerequisites

- Kubernetes 1.24+ with:
  - Ingress controller (e.g., `ingress-nginx`)
  - Prometheus Operator (for `ServiceMonitor`)
  - Cert-Manager (for automatic TLS if you use the example annotations)
- `kubectl` with cluster admin permissions for initial namespace creation
- Container registry access to push/pull `mycelium-fractal-net:v4.1`

## 1) Create namespace and security budgets

```bash
kubectl apply -f k8s.yaml -n mycelium-fractal-net --dry-run=client
kubectl apply -f k8s.yaml -n mycelium-fractal-net --prune=false
```

The manifest creates:
- **Namespace** with Pod Security labels set to `restricted`
- **LimitRange** and **ResourceQuota** to enforce per-pod defaults and namespace caps
- **ServiceAccount** with `automountServiceAccountToken: false`
- **PodDisruptionBudget** to keep at least two pods available during node drain/updates
- **Pod anti-affinity** to spread replicas across nodes

### Terraform bootstrap (IaC)

For reproducible infrastructure bootstrapping, use the Terraform module in `infra/terraform` to create the namespace and service account:

```bash
cd infra/terraform
terraform init
terraform apply -var="kubeconfig_path=~/.kube/config"
```

## 2) Configure secrets (mandatory)

Set API keys via Kubernetes Secrets (never bake them into images):

```bash
kubectl create secret generic mfn-secrets \
  --from-literal=api-key="$(openssl rand -base64 32)" \
  --from-literal=api-keys="key-primary,key-rotated" \
  -n mycelium-fractal-net
```

The deployment consumes:
- `MFN_API_KEY` (single primary key)
- `MFN_API_KEYS` (comma-separated allow-list for rotation)

## 3) Configure non-secret settings (ConfigMap)

`k8s.yaml` includes `mfn-app-env`, providing sane production defaults. Override before apply to match your environment:

```bash
kubectl create configmap mfn-app-env \
  --from-literal=MFN_ENV=prod \
  --from-literal=MFN_API_KEY_REQUIRED=true \
  --from-literal=MFN_RATE_LIMIT_ENABLED=true \
  --from-literal=MFN_RATE_LIMIT_REQUESTS=100 \
  --from-literal=MFN_RATE_LIMIT_WINDOW=60 \
  --from-literal=MFN_CORS_ORIGINS="https://mfn.example.com" \
  --from-literal=MFN_METRICS_ENABLED=true \
  --from-literal=MFN_METRICS_ENDPOINT=/metrics \
  --from-literal=MFN_LOG_FORMAT=json \
  --from-literal=MFN_LOG_LEVEL=INFO \
  --dry-run=client -o yaml | kubectl apply -f -
```

Additional config:
- `mycelium-config` ConfigMap carries the simulation JSON payload mounted into the pod.
- Ingress annotations expect a TLS secret named `mfn-tls-secret`; adjust for your issuer/hostname.

## 4) Deploy and validate

```bash
kubectl apply -f k8s.yaml
kubectl -n mycelium-fractal-net get deploy,po,svc,ingress,hpa,pdb,serviceaccount
kubectl -n mycelium-fractal-net logs deploy/mycelium-fractal-net -f
```

Health expectations:
- `startupProbe` and `livenessProbe` target `/health`
- `ServiceMonitor` scrapes the configured metrics path (default: `/metrics`) on port `http`
- Ingress publishes HTTPS at `https://mfn.example.com/` (update host as needed)

## 5) Observability and rate limiting

- **Metrics**: Prometheus-compatible metrics are exposed via `MFN_METRICS_ENDPOINT` (default: `/metrics`) and scraped by `ServiceMonitor mfn-metrics`.
- **Logging**: Structured JSON logs include `X-Request-ID` for correlation.
- **Rate limiting**: Defaults to 100 req/min with a 60s window. Adjust `MFN_RATE_LIMIT_REQUESTS` and `MFN_RATE_LIMIT_WINDOW` in `mfn-app-env`.
- **Headers**: Rate-limit headers (`X-RateLimit-*`) and request ID (`X-Request-ID`) are returned on protected routes.

## 6) Network and security posture

- **NetworkPolicy** only allows ingress from the ingress controller namespace and monitoring namespace; egress is restricted to DNS and HTTPS.
- **ServiceAccount** is non-privileged with tokens disabled by default; pods run as non-root with a read-only root filesystem and `seccompProfile: RuntimeDefault`.
- **Resource governance**: LimitRange and ResourceQuota prevent noisy-neighbor issues and align with the HPA (min 3, max 100) while capping total CPU/memory and ephemeral storage.
- **Certificates**: Enable TLS via Cert-Manager annotations or supply your own secret (`mfn-tls-secret`).

### Access control and Zero Trust

- Enforce **MFA** for all cluster access via your identity provider and Git hosting.
- Use **short-lived credentials** (OIDC) for CI/CD to avoid long-lived secrets.
- Treat the cluster network as untrusted: enforce namespace isolation, least-privilege RBAC, and explicit egress allowlists.

## 7) Rolling updates and scaling

- **HPA** targets 70% CPU / 80% memory utilization across replicas.
- **Pod anti-affinity** keeps replicas on different nodes; adjust if your cluster has fewer nodes.
- For controlled rollouts: `kubectl rollout status deploy/mycelium-fractal-net` and `kubectl rollout undo deploy/mycelium-fractal-net`.

## 8) GitOps deployment (ArgoCD)

An example ArgoCD `Application` manifest is provided in `infra/gitops/argocd-application.yaml`.
Update `repoURL` and `targetRevision`, then apply it to your ArgoCD namespace:

```bash
kubectl apply -f infra/gitops/argocd-application.yaml -n argocd
```

This keeps deployment state aligned with Git, supports automated drift correction, and integrates cleanly with CI/CD.
