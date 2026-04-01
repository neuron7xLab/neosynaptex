# ADR 0009: API Versioning Strategy

**Status:** Accepted  
**Date:** 2026-01-20  
**Authors:** Technical Debt Resolution Team  
**Decision Makers:** Engineering Team

---

## Context

The MLSDM Neuro Cognitive Engine exposes a REST API for text generation, event processing, and system state management. As the system evolves, API changes are inevitable. Without a clear versioning strategy, breaking changes could disrupt existing clients and integrations.

### Problem Statement

We need a versioning strategy that:
1. Prevents breaking changes from affecting existing clients
2. Allows iterative API improvements without backward compatibility burden
3. Provides clear communication about API stability
4. Enables gradual migration for API consumers
5. Integrates with automated contract validation

### Requirements

- **Backward Compatibility:** Existing clients must continue to work after deployments
- **Clear Deprecation Path:** Old versions should have documented EOL timelines
- **Automated Validation:** Breaking changes should be detected in CI
- **Minimal Overhead:** Versioning shouldn't add significant development friction
- **OpenAPI Support:** Must work with FastAPI's OpenAPI generation

---

## Decision

We will use **URL path-based versioning** with explicit version prefixes (`/v1/`, `/v2/`, etc.) for all API endpoints, excluding health and metrics endpoints which remain unversioned.

### Implementation Details

#### 1. Version Prefix Structure

```
/v1/generate      # Version 1 of generate endpoint
/v2/generate      # Version 2 (may have different request/response)
/health           # Unversioned (always backward compatible)
/health/ready     # Unversioned
/health/metrics   # Unversioned (Prometheus standard)
```

#### 2. FastAPI Router Organization

```python
# Versioned routers for API stability
v1_router = APIRouter(prefix="/v1")
v2_router = APIRouter(prefix="/v2")

# Endpoints registered on specific version routers
@v1_router.post("/generate")
async def generate_v1(request: GenerateRequest) -> GenerateResponse:
    # V1 implementation
    pass

@v2_router.post("/generate")
async def generate_v2(request: GenerateRequestV2) -> GenerateResponseV2:
    # V2 implementation with enhanced features
    pass
```

#### 3. Version Lifecycle

- **Current:** v1 (stable, production)
- **Next:** v2 (preview, available but may change)
- **Deprecated:** (none currently)

**Deprecation Process:**
1. New version announced (e.g., v3 released)
2. Previous stable version (v1) marked deprecated with 6-month EOL warning
3. After 6 months, deprecated version removed

#### 4. Breaking Change Detection

Automated CI workflow validates:
- No endpoints removed from existing versions
- No required fields removed from request schemas
- No response fields removed
- No change in endpoint semantics

Breaking changes require:
- New version number (v2, v3, etc.)
- Documentation update
- Migration guide
- Approval label on PR

#### 5. Contract Validation

OpenAPI baseline stored in `docs/openapi-baseline.json`:
- Generated on every release
- Compared against current spec in CI
- Breaking changes block PRs unless approved

---

## Alternatives Considered

### 1. Header-Based Versioning

```http
GET /generate
Accept-Version: v1
```

**Pros:**
- Clean URLs
- More RESTful

**Cons:**
- Less discoverable
- Harder to test with curl/browser
- Not visible in API documentation
- FastAPI doesn't have native support

**Decision:** Rejected due to discoverability and tooling issues

### 2. Query Parameter Versioning

```http
GET /generate?version=v1
```

**Pros:**
- Backward compatible (default version if omitted)
- Easy to implement

**Cons:**
- Not RESTful
- Clutters URLs
- Inconsistent with OpenAPI standards

**Decision:** Rejected due to poor semantics

### 3. Domain-Based Versioning

```http
https://v1.api.example.com/generate
https://v2.api.example.com/generate
```

**Pros:**
- Clear separation
- Independent scaling
- Easy traffic routing

**Cons:**
- Infrastructure complexity
- Certificate management
- Not suitable for self-hosted deployments

**Decision:** Rejected due to operational overhead

### 4. No Versioning (Continuous Evolution)

Maintain backward compatibility forever.

**Pros:**
- Simpler development
- No version management

**Cons:**
- Technical debt accumulation
- Inability to fix design mistakes
- Eventual codebase pollution

**Decision:** Rejected due to long-term maintainability concerns

---

## Consequences

### Positive

1. **Clear Contract:** Clients know exactly which version they're using
2. **Safe Iteration:** We can improve the API without breaking existing integrations
3. **Automated Safety:** CI prevents accidental breaking changes
4. **OpenAPI Standard:** Works seamlessly with FastAPI's OpenAPI generation
5. **Self-Documenting:** Version is visible in every request
6. **Gradual Migration:** Clients can migrate at their own pace

### Negative

1. **Code Duplication:** May duplicate logic across versions
2. **Testing Overhead:** Must test multiple versions
3. **Documentation Burden:** Each version needs documentation
4. **Maintenance Windows:** Old versions require security patches

### Mitigations

- **Shared Business Logic:** Extract common logic to shared modules
- **Focused Testing:** Focus integration tests on stable versions
- **Clear EOL Policy:** Communicate deprecation timelines early
- **Migration Guides:** Provide clear upgrade paths

---

## Implementation Checklist

- [x] Create versioned routers (v1_router, v2_router)
- [x] Migrate existing endpoints to v1
- [x] Add v2 router for future enhancements
- [x] Create OpenAPI baseline
- [x] Implement CI contract validation workflow
- [x] Add make targets: `validate-api-contract`, `update-api-baseline`
- [x] Document versioning strategy in ADR
- [ ] Add migration guide template
- [ ] Update API documentation with version info

---

## References

- **FastAPI Versioning:** https://fastapi.tiangolo.com/advanced/sub-applications/
- **OpenAPI Specification:** https://spec.openapis.org/oas/v3.1.0
- **API Versioning Best Practices:** https://www.troyhunt.com/your-api-versioning-is-wrong/
- **Technical Debt Register:** TD-007 - Formal API Contract Validation

---

## Review History

| Date       | Reviewer | Status   | Comments |
|------------|----------|----------|----------|
| 2026-01-20 | Engineering Team | Accepted | Implemented as part of TD-007 resolution |

---

**Supersedes:** None  
**Superseded by:** None
