# CALIBRATION MAP

This document provides a comprehensive inventory of all calibrated thresholds, tolerances, and sensitivity parameters in the MLSDM system.

## Quick Reference

| Parameter Category | Role | Critical for |
|-------------------|------|--------------|
| Moral Filter | SAFETY | Content governance, toxic rejection |
| Aphasia Detector | QUALITY | Output coherence, telegraphic detection |
| Secure Mode | SAFETY | Production lockdown, training prevention |
| PELM | MEMORY | Retrieval precision, resource usage |
| Synaptic Memory | MEMORY | Consolidation, decay rates |
| Cognitive Rhythm | QUALITY/PERF | Wake/sleep cycles, token limits |
| Reliability | PERF | Circuit breakers, retry logic |
| Rate Limiting | SECURITY | API abuse prevention |

---

## 1. Moral Filter Parameters

**Role**: SAFETY - Critical for preventing toxic/harmful content

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `threshold` | `config/calibration.py:39` | 0.50 | ↑ stricter (more rejections) | Initial moral threshold |
| `adapt_rate` | `config/calibration.py:43` | 0.05 | ↑ faster adaptation | Threshold adjustment rate |
| `min_threshold` | `config/calibration.py:47` | 0.30 | ↑ higher safety floor | Minimum allowed threshold |
| `max_threshold` | `config/calibration.py:51` | 0.90 | ↑ allows stricter | Maximum allowed threshold |
| `dead_band` | `config/calibration.py:55` | 0.05 | ↑ less sensitive | EMA dead band (MoralFilterV2) |
| `ema_alpha` | `config/calibration.py:59` | 0.1 | ↑ more recent weight | EMA smoothing factor |

**Code References**:
- `src/mlsdm/cognition/moral_filter.py` (MoralFilter)
- `src/mlsdm/cognition/moral_filter_v2.py` (MoralFilterV2)
- `config/default_config.yaml` (moral_filter section)

---

## 2. Aphasia-Broca Detector Parameters

**Role**: QUALITY - Ensures coherent, grammatically complete responses

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `min_sentence_len` | `config/calibration.py:78` | 6.0 | ↑ stricter detection | Min avg sentence length |
| `min_function_word_ratio` | `config/calibration.py:82` | 0.15 | ↑ stricter detection | Min function word ratio |
| `max_fragment_ratio` | `config/calibration.py:86` | 0.5 | ↑ more permissive | Max fragment sentence ratio |
| `fragment_length_threshold` | `config/calibration.py:90` | 4 | ↑ more fragments detected | Token count for fragments |
| `severity_threshold` | `config/calibration.py:94` | 0.3 | ↑ fewer repairs | Min severity for repair |
| `detect_enabled` | `config/calibration.py:97` | true | Boolean | Enable detection |
| `repair_enabled` | `config/calibration.py:100` | true | Boolean | Enable LLM-based repair |

**Code References**:
- `src/mlsdm/extensions/neuro_lang_extension.py` (AphasiaBrocaDetector)
- `src/mlsdm/extensions/neuro_lang_extension.py` (AphasiaSpeechGovernor)
- `config/default_config.yaml` (aphasia section)

---

## 3. Secure Mode Parameters

**Role**: SAFETY - Production lockdown, prevents training

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `env_var_name` | `config/calibration.py:117` | MLSDM_SECURE_MODE | String | Environment variable |
| `enabled_values` | `config/calibration.py:120` | ("1", "true", "TRUE") | Tuple | Values that enable |
| `disable_neurolang_training` | `config/calibration.py:126` | true | Boolean | Block NeuroLang |
| `disable_checkpoint_loading` | `config/calibration.py:127` | true | Boolean | Block checkpoints |
| `disable_aphasia_repair` | `config/calibration.py:128` | true | Boolean | Detection only |

**Code References**:
- `src/mlsdm/extensions/neuro_lang_extension.py` (is_secure_mode_enabled)

---

## 4. PELM (Phase-Entangled Lattice Memory) Parameters

**Role**: MEMORY/PERFORMANCE - Affects recall quality and resource usage

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `default_capacity` | `config/calibration.py:146` | 20,000 | ↑ more memory | Max vectors stored |
| `max_capacity` | `config/calibration.py:149` | 1,000,000 | ↑ higher ceiling | Hard maximum |
| `phase_tolerance` | `config/calibration.py:153` | 0.15 | ↑ more matches | Phase matching tolerance |
| `default_top_k` | `config/calibration.py:157` | 5 | ↑ more results | Default retrieval count |
| `min_norm_threshold` | `config/calibration.py:160` | 1e-9 | ↑ safer division | Zero-division guard |
| `wake_phase` | `config/calibration.py:163` | 0.1 | Float | Wake phase encoding |
| `sleep_phase` | `config/calibration.py:166` | 0.9 | Float | Sleep phase encoding |

**Code References**:
- `src/mlsdm/memory/phase_entangled_lattice_memory.py` (PhaseEntangledLatticeMemory)
- `src/mlsdm/core/cognitive_controller.py` (retrieve_context)
- `src/mlsdm/utils/config_schema.py` (PELMConfig)

---

## 5. Multi-Level Synaptic Memory Parameters

**Role**: MEMORY - Controls memory consolidation and decay

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `lambda_l1` | `config/calibration.py:184` | 0.50 | ↑ faster decay | L1 (short-term) decay |
| `lambda_l2` | `config/calibration.py:188` | 0.10 | ↑ faster decay | L2 (medium-term) decay |
| `lambda_l3` | `config/calibration.py:192` | 0.01 | ↑ faster decay | L3 (long-term) decay |
| `theta_l1` | `config/calibration.py:196` | 1.2 | ↑ harder consolidate | L1→L2 threshold |
| `theta_l2` | `config/calibration.py:200` | 2.5 | ↑ harder consolidate | L2→L3 threshold |
| `gating12` | `config/calibration.py:204` | 0.45 | ↑ more transfer | L1→L2 gating |
| `gating23` | `config/calibration.py:208` | 0.30 | ↑ more transfer | L2→L3 gating |

**Code References**:
- `src/mlsdm/memory/multi_level_memory.py` (MultiLevelSynapticMemory)
- `config/default_config.yaml` (multi_level_memory section)
- `src/mlsdm/utils/config_schema.py` (MultiLevelMemoryConfig)

---

## 6. Cognitive Rhythm Parameters

**Role**: QUALITY/PERFORMANCE - Controls wake/sleep cycles

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `wake_duration` | `config/calibration.py:226` | 8 | ↑ longer active | Wake steps |
| `sleep_duration` | `config/calibration.py:230` | 3 | ↑ longer consolidation | Sleep steps |
| `max_wake_tokens` | `config/calibration.py:233` | 2048 | ↑ longer responses | Wake token limit |
| `max_sleep_tokens` | `config/calibration.py:236` | 150 | ↑ longer responses | Sleep token limit |

**Code References**:
- `src/mlsdm/rhythm/cognitive_rhythm.py` (CognitiveRhythm)
- `src/mlsdm/core/llm_wrapper.py` (MAX_WAKE_TOKENS, MAX_SLEEP_TOKENS)
- `config/default_config.yaml` (cognitive_rhythm section)

---

## 7. LLM Wrapper Reliability Parameters

**Role**: PERFORMANCE/RELIABILITY - Controls resilience

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `circuit_breaker_failure_threshold` | `config/calibration.py:254` | 5 | ↑ more tolerant | Failures to open |
| `circuit_breaker_recovery_timeout` | `config/calibration.py:258` | 60.0 | ↑ longer wait | Seconds before half-open |
| `circuit_breaker_success_threshold` | `config/calibration.py:262` | 2 | ↑ more cautious | Successes to close |
| `llm_timeout` | `config/calibration.py:266` | 30.0 | ↑ more patient | LLM call timeout (s) |
| `llm_retry_attempts` | `config/calibration.py:270` | 3 | ↑ more persistent | Retry attempts |
| `pelm_failure_threshold` | `config/calibration.py:274` | 3 | ↑ more tolerant | Failures before stateless |

**Code References**:
- `src/mlsdm/core/llm_wrapper.py` (CircuitBreaker, LLMWrapper)

---

## 8. Synergy Experience Parameters

**Role**: QUALITY - Adaptive behavior learning

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `epsilon` | `config/calibration.py:292` | 0.1 | ↑ more exploration | ε-greedy exploration |
| `neutral_tolerance` | `config/calibration.py:296` | 0.01 | ↑ wider neutral zone | Delta neutral threshold |
| `min_trials_for_confidence` | `config/calibration.py:300` | 3 | ↑ more cautious | Min trials for trust |
| `ema_alpha` | `config/calibration.py:304` | 0.2 | ↑ recent weight | EMA smoothing |

**Code References**:
- `src/mlsdm/cognition/synergy_experience.py`
- `src/mlsdm/utils/config_schema.py` (SynergyExperienceConfig)

---

## 9. Rate Limiting Parameters

**Role**: SECURITY/PERFORMANCE - API abuse prevention

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `requests_per_window` | `config/calibration.py:322` | 100 | ↑ more permissive | Requests per window |
| `window_seconds` | `config/calibration.py:326` | 60 | ↑ longer window | Window duration (s) |
| `storage_cleanup_interval` | `config/calibration.py:330` | 300 | ↑ less cleanup | Cleanup interval (s) |

**Code References**:
- `src/mlsdm/security/rate_limit.py` (RateLimiter)

---

## 10. Cognitive Controller Parameters

**Role**: PERFORMANCE/SAFETY - Resource management

| Name | Location | Current Value | Direction of Effect | Description |
|------|----------|---------------|---------------------|-------------|
| `memory_threshold_mb` | `config/calibration.py:348` | 1024.0 | ↑ higher limit | Emergency shutdown MB |
| `max_processing_time_ms` | `config/calibration.py:352` | 1000.0 | ↑ more patient | Max event processing ms |

**Code References**:
- `src/mlsdm/core/cognitive_controller.py` (CognitiveController)

---

## Configuration Override Hierarchy

Parameters can be configured at three levels (in order of precedence):

1. **Environment Variables** (highest priority)
   - Format: `MLSDM_<SECTION>__<KEY>=<value>`
   - Example: `MLSDM_MORAL_FILTER__THRESHOLD=0.7`

2. **Config Files** (config/*.yaml)
   - Load with: `ConfigLoader.load_config("config/production.yaml")`

3. **Calibration Defaults** (config/calibration.py)
   - Hardcoded baseline values in this module

---

## Safety-Critical Parameters

The following parameters are **critical for safety** and should be changed with extreme caution:

| Parameter | Module | Risk if Misconfigured |
|-----------|--------|----------------------|
| `moral_filter.threshold` | Moral Filter | Too low → toxic content passes |
| `moral_filter.min_threshold` | Moral Filter | Floor for adaptive lowering |
| `secure_mode.*` | Secure Mode | Disabling allows training in prod |
| `aphasia.severity_threshold` | Aphasia | Too high → broken responses pass |
| `rate_limit.requests_per_window` | Rate Limit | Too high → DoS vulnerability |

---

## Performance-Critical Parameters

The following parameters significantly impact **latency and resource usage**:

| Parameter | Impact |
|-----------|--------|
| `pelm.default_capacity` | Memory usage scales linearly |
| `pelm.phase_tolerance` | Wider → more candidates → slower |
| `cognitive_rhythm.max_wake_tokens` | Response length and latency |
| `reliability.llm_timeout` | Maximum request duration |
| `cognitive_controller.max_processing_time_ms` | Per-event latency budget |

---

## Calibration Workflow

To recalibrate parameters:

1. Run calibration benchmarks: `python scripts/run_calibration_benchmarks.py`
2. Analyze results in `docs/CALIBRATION_RESULTS.md`
3. Update values in `config/calibration.py`
4. Run full test suite: `pytest tests/ --ignore=tests/load`
5. Validate with evaluation scripts: `python scripts/run_aphasia_eval.py`
