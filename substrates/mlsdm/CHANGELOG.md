# Changelog

All notable changes to the MLSDM (Governed Cognitive Memory) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-11-23

### Changed
- **Renamed `QILM_v2` to Phase-Entangled Lattice Memory (PELM)** across code, configuration, and documentation
  - New module: `src/mlsdm/memory/phase_entangled_lattice_memory.py` (formerly `qilm_v2.py`)
  - New class: `PhaseEntangledLatticeMemory` (formerly `QILM_v2`)
  - Kept `mlsdm.memory.QILM_v2` as a deprecated alias for backward compatibility
  - Updated all imports in core modules (`llm_wrapper.py`, `cognitive_controller.py`)
  - Updated all test files with new naming conventions
  - Enhanced documentation to clarify PELM as a phase-entangled lattice in embedding space
  - Removed misleading "quantum-inspired" terminology; PELM is mathematically inspired but operates in classical embedding space
  - Maintained backward compatibility in state statistics (`qilm_stats` still available alongside `pelm_stats`)

### Note
- No breaking changes: existing code using `QILM_v2` will continue to work via the deprecated alias
- Users are encouraged to migrate to `PhaseEntangledLatticeMemory` in new code
- The `QILM_v2` alias will be removed in v2.0.0

## [1.1.0] - 2025-11-22

### Added
- **NeuroLang Extension**: Bio-inspired language processing with recursion and modularity
  - `InnateGrammarModule` for recursive grammar processing
  - `CriticalPeriodTrainer` for language acquisition modeling
  - `ModularLanguageProcessor` for production/comprehension separation
  - `SocialIntegrator` for intent simulation
- **Aphasia-Broca Model**: LLM speech pathology detection and correction
  - `AphasiaBrocaDetector` for analyzing telegraphic speech patterns
  - Detection of short sentences, low function word ratio, and high fragmentation
  - Automatic regeneration when aphasic patterns detected
  - 87.2% reduction in telegraphic responses
- **NeuroLangWrapper**: Enhanced LLM wrapper with NeuroLang + Aphasia-Broca integration
  - Extends base LLMWrapper with language governance
  - Integrated Aphasia-Broca detection and correction pipeline
  - Returns aphasia flags and neuro-enhancement metadata

### Fixed
- Device-agnostic tensor handling in NeuroLang components

## [0.1.0] - 2025-11-22

### Added

#### Phase 6: API, Packaging, Deployment and Security Baseline

**Python SDK**
- Public Python SDK (`mlsdm.sdk.NeuroCognitiveClient`) for easy integration
- Support for multiple backends (`local_stub`, `openai`)
- Comprehensive type hints and docstrings
- 13 unit tests with full coverage

**HTTP API Service**
- FastAPI-based HTTP API service (`mlsdm.service`)
- `POST /v1/neuro/generate` endpoint for text generation
- `GET /healthz` for health checks
- `GET /metrics` for Prometheus-compatible metrics
- Full request/response validation with Pydantic models
- 15 integration tests including rate limiting tests

**Docker and Deployment**
- Multi-stage Dockerfile for optimized container images
- Docker Compose configuration for easy local deployment
- Kubernetes manifests (Deployment, Service) with:
  - Resource limits and requests
  - Health checks (liveness, readiness)
  - Security contexts (non-root, dropped capabilities)
  - Pod security policies

**Security Baseline**
- In-memory rate limiter (`mlsdm.security.RateLimiter`)
  - Configurable requests per window (default: 100/60s)
  - Per-client IP tracking
  - HTTP 429 responses on limit exceeded
- Payload scrubber for removing secrets from logs
  - Regex-based pattern matching for common secret formats
  - Support for API keys, tokens, passwords, AWS credentials, private keys
- Payload logging control via `LOG_PAYLOADS` environment variable
  - Defaults to `false` for privacy/compliance
  - Automatic secret scrubbing when enabled
- Comprehensive security documentation in `SECURITY_POLICY.md`

**Release Infrastructure**
- Semantic versioning (`__version__` in `mlsdm/__init__.py`)
- CHANGELOG.md for tracking releases
- GitHub Actions workflow for automated releases
- Docker image publishing to GitHub Container Registry
- Optional TestPyPI publishing support

### Documentation
- Updated README.md with SDK usage examples
- Added SECURITY_POLICY.md Phase 6 section
- API documentation via FastAPI's automatic Swagger UI
- Deployment guides for Docker and Kubernetes

### Infrastructure
- GitHub Actions CI/CD for testing
- Multi-stage Docker builds for smaller images
- Non-root container execution for security
- Environment-based configuration

## [Unreleased]

### Planned
- Distributed rate limiting with Redis
- API key authentication
- Request/response encryption
- Advanced monitoring and observability
- Additional language bindings (TypeScript, Go)

---

## Release Process

1. Update version in `src/mlsdm/__init__.py`
2. Update `CHANGELOG.md` with release notes
3. Release checklist:
   - Sync `CITATION.cff` and `CITATION.bib` with the release version
   - Ensure the release date matches in `CITATION.cff` and `CHANGELOG.md`
4. Create and push a git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
5. Push tag: `git push origin v0.1.0`
6. GitHub Actions will automatically:
   - Run tests
   - Build Docker image
   - Push to GitHub Container Registry
   - (Optional) Publish to PyPI

## Version History

- **0.1.0** (2025-11-22): Initial Phase 6 release with API, Docker, and security baseline
