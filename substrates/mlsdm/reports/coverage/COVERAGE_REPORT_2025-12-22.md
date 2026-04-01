# Coverage Report — 2025-12-22

- Command: `python -m pytest tests/unit/ tests/state/ --cov=src/mlsdm --cov-report=term-missing --cov-report=xml:coverage.xml -m 'not slow' -q --tb=short`
- Total coverage: **78.62%**

## Top 10 lowest-covered modules (term-missing)
1. src/mlsdm/extensions/neuro_lang_extension.py — 48.17%
2. src/mlsdm/observability/logger.py — 57.08%
3. src/mlsdm/observability/metrics.py — 65.88%
4. src/mlsdm/observability/tracing.py — 68.59%
5. src/mlsdm/state/system_state_store.py — 72.62%
6. src/mlsdm/security/oidc.py — 73.97%
7. src/mlsdm/engine/neuro_cognitive_engine.py — 74.95%
8. src/mlsdm/observability/memory_telemetry.py — 75.49%
9. src/mlsdm/security/rate_limit.py — 76.54%
10. src/mlsdm/security/payload_scrubber.py — 78.95%

## Coverage improvements
- Expanded safety analyzer coverage for conversation pattern detection and context sanitization (`tests/unit/test_llm_safety_comprehensive.py`).
- Added secure payload/log scrubbing and secure-mode flag checks (`tests/unit/test_payload_scrubber.py`).
- Exercised OIDC configuration parsing, JWKS caching, and token extraction (`tests/unit/test_oidc_config_and_cache.py`).
- Covered migration path registration and error handling for system state upgrades (`tests/state/test_system_state_migrations_paths.py`).
