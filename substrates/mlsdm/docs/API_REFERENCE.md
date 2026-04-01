# API Reference

**Document Version:** 1.2.0
**Project Version:** 1.2.0
**Last Updated:** December 2025
**Status:** Production

Complete API reference for MLSDM Governed Cognitive Memory v1.2.0.

## Table of Contents

- [API Versioning](#api-versioning)
- [HTTP API Endpoints](#http-api-endpoints)
  - [Health Check](#health-check)
  - [Generate](#generate)
- [LLMWrapper](#llmwrapper)
- [CognitiveController](#cognitivecontroller)
- [Memory Components](#memory-components)
  - [PELM](#qilm_v2)
  - [MultiLevelSynapticMemory](#multilevelsyn apticmemory)
- [Filtering Components](#filtering-components)
  - [MoralFilterV2](#moralfilterv2)
  - [OntologyMatcher](#ontologymatcher)
- [Rhythm Components](#rhythm-components)
  - [CognitiveRhythm](#cognitiverhythm)
- [Utilities](#utilities)
  - [MetricsCollector](#metricscollector)

---

## API Versioning (DOC-002)

### Versioning Scheme

MLSDM follows **Semantic Versioning 2.0.0** (semver):

```
MAJOR.MINOR.PATCH
  │     │     └── Bug fixes, no breaking changes
  │     └──────── New features, backwards compatible
  └────────────── Breaking changes
```

**Current Version:** 1.2.0

### API Version Header

All API responses include the API version in headers:

```
X-MLSDM-API-Version: 1.2.0
X-MLSDM-Min-Supported-Version: 1.0.0
```

### Version Compatibility

| API Version | Status | Support Until |
|-------------|--------|---------------|
| **1.x** | ✅ Current | Active support |
| 0.x | ⚠️ Deprecated | December 2025 |

### Breaking Change Policy

**Breaking changes** are introduced only in MAJOR version increments. Examples:

- Removing an endpoint
- Removing a required field from responses
- Changing the meaning of a field
- Changing authentication requirements

**Non-breaking changes** (MINOR/PATCH):

- Adding new optional request parameters
- Adding new fields to responses
- Adding new endpoints
- Adding new error codes
- Performance improvements
- Bug fixes

### Deprecation Timeline

1. **Deprecation Notice**: Feature marked deprecated in MINOR release
   - Deprecation warning added to docs
   - `Deprecation` header added to responses
   - Minimum 3 months notice

2. **Migration Period**: 3-6 months
   - Feature continues to work
   - Migration guide published
   - New alternative documented

3. **Removal**: In next MAJOR release
   - Feature removed
   - CHANGELOG updated
   - Migration complete

### Deprecated Features

| Feature | Deprecated In | Removed In | Migration |
|---------|---------------|------------|-----------|
| `/v0/generate` | 1.0.0 | 2.0.0 | Use `/generate` |

### Response Headers for Deprecation

Deprecated endpoints include headers:

```
Deprecation: true
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Link: </docs/migration>; rel="deprecation"; type="text/html"
```

### OpenAPI Specification

The OpenAPI specification is auto-generated and available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **JSON Spec**: `http://localhost:8000/openapi.json`
- **Static Export**: `docs/openapi.json` (regenerated on release)

To export the spec manually:

```bash
python scripts/export_openapi.py --output docs/openapi.json
```

### Client SDK Compatibility

When upgrading, check client SDK compatibility:

| SDK | Compatible API Versions |
|-----|------------------------|
| Python SDK | 1.0.0 - 1.2.x |
| TypeScript SDK | 1.1.0 - 1.2.x |

### Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and breaking changes.

---

## HTTP API Endpoints

The MLSDM HTTP API provides RESTful endpoints for text generation with cognitive governance.

### Starting the Server

```bash
# Start with uvicorn
uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000

# With environment variables
CONFIG_PATH=config/production.yaml uvicorn mlsdm.api.app:app --host 0.0.0.0 --port 8000
```

### Request Headers

#### X-MLSDM-Priority (REL-005)

Priority header for request prioritization. High-priority requests are processed before lower-priority ones when the system is under load.

**Header:** `X-MLSDM-Priority`

**Values:**
| Value | Weight | Description |
|-------|--------|-------------|
| `high` | 3 | High priority - processed first under load |
| `normal` | 2 | Normal priority (default) |
| `low` | 1 | Low priority - processed last under load |
| `1-3` | - | Numeric alias for `low` |
| `4-6` | - | Numeric alias for `normal` |
| `7-10` | - | Numeric alias for `high` |

**Example:**
```bash
# High priority request
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-MLSDM-Priority: high" \
  -d '{"prompt": "Critical request"}'

# Using numeric priority
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-MLSDM-Priority: 9" \
  -d '{"prompt": "High priority"}'
```

**Response Header:**
- `X-MLSDM-Priority-Applied`: Returns the applied priority level

**Notes:**
- Default priority is `normal` when header is not provided
- Priority only affects request ordering under load (when bulkhead is full)
- All priority levels have the same timeout and quality guarantees

### Health Check

Simple health check endpoint to verify service is running.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy"
}
```

**Response Model:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "healthy" if service is responsive |

**Example:**
```bash
curl http://localhost:8000/health
```

### Generate

Generate text using the NeuroCognitiveEngine with moral governance.

**Endpoint:** `POST /generate`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Input text to process (min 1 character) |
| `max_tokens` | integer | No | Maximum tokens to generate (1-4096) |
| `moral_value` | float | No | Moral threshold value (0.0-1.0) |

**Response Model:**

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Generated response text |
| `phase` | string | Current cognitive phase ("wake" or "sleep") |
| `accepted` | boolean | Whether the request was accepted |
| `metrics` | object \| null | Performance timing metrics |
| `safety_flags` | object \| null | Safety validation results |
| `memory_stats` | object \| null | Memory state statistics |

**Success Response (200):**
```json
{
  "response": "Generated response text...",
  "phase": "wake",
  "accepted": true,
  "metrics": {
    "timing": {
      "total": 15.2,
      "generation": 10.5,
      "moral_precheck": 2.1
    }
  },
  "safety_flags": {
    "validation_steps": [
      {"step": "moral_precheck", "passed": true, "score": 0.85, "threshold": 0.5}
    ],
    "rejected_at": null
  },
  "memory_stats": {
    "step": 1,
    "moral_threshold": 0.5,
    "context_items": 3
  }
}
```

**Error Responses:**

| Status | Condition | Response |
|--------|-----------|----------|
| 400 | Invalid input (e.g., whitespace-only prompt) | `{"error": {"error_type": "validation_error", "message": "...", "details": {...}}}` |
| 422 | Validation failed (missing/invalid fields) | `{"detail": [...]}` |
| 429 | Rate limit exceeded | `{"error": {"error_type": "rate_limit_exceeded", "message": "...", "details": null}}` |
| 500 | Internal server error | `{"error": {"error_type": "internal_error", "message": "...", "details": null}}` |

**Examples:**

```bash
# Basic request
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain machine learning"}'

# With all parameters
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain machine learning", "max_tokens": 200, "moral_value": 0.8}'
```

---

## LLMWrapper

Universal wrapper for any LLM with cognitive governance and biological constraints.

### Constructor

```python
LLMWrapper(
    llm_generate_fn: Callable[[str, int], str],
    embedding_fn: Callable[[str], np.ndarray],
    dim: int = 384,
    capacity: int = 20000,
    wake_duration: int = 8,
    sleep_duration: int = 3,
    initial_moral_threshold: float = 0.50,
    llm_timeout: float = 30.0,
    llm_retry_attempts: int = 3,
    speech_governor: Optional[SpeechGovernor] = None
)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `llm_generate_fn` | Callable | Required | Function that takes (prompt: str, max_tokens: int) and returns generated text |
| `embedding_fn` | Callable | Required | Function that takes text: str and returns embedding as np.ndarray |
| `dim` | int | 384 | Dimension of embeddings (must match embedding_fn output) |
| `capacity` | int | 20000 | Maximum number of vectors in memory |
| `wake_duration` | int | 8 | Number of steps in wake phase |
| `sleep_duration` | int | 3 | Number of steps in sleep phase |
| `initial_moral_threshold` | float | 0.50 | Initial moral filtering threshold (0.30-0.90) |
| `llm_timeout` | float | 30.0 | Timeout for LLM calls in seconds |
| `llm_retry_attempts` | int | 3 | Number of retry attempts for LLM calls |
| `speech_governor` | SpeechGovernor | None | Optional speech governance policy (see [Speech Governance](#speech-governance)) |

**Raises:**
- `ValueError`: If parameters are invalid

**Example:**
```python
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np

def my_llm(prompt: str, max_tokens: int) -> str:
    return "Generated response"

def my_embed(text: str) -> np.ndarray:
    return np.random.randn(384).astype(np.float32)

wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    dim=384
)
```

### Methods

#### generate

Generate text with cognitive governance.

```python
def generate(
    prompt: str,
    moral_value: float,
    max_tokens: Optional[int] = None,
    context_top_k: int = 5
) -> dict
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | str | Required | Input prompt text |
| `moral_value` | float | Required | Moral acceptability score (0.0-1.0) |
| `max_tokens` | int | None | Override default max tokens |
| `context_top_k` | int | 5 | Number of context items to retrieve |

**Returns:** Dictionary with keys:
- `response` (str): Generated text (empty if rejected)
- `accepted` (bool): Whether request was accepted
- `phase` (str): Current phase ("wake" or "sleep")
- `step` (int): Current step counter
- `note` (str): Processing note
- `moral_threshold` (float): Current moral threshold
- `context_items` (int): Number of context items retrieved
- `max_tokens_used` (int): Max tokens used for generation
- `speech_governance` (dict, optional): Speech governance metadata (if governor configured)
  - `raw_text` (str): Original LLM output before governance
  - `metadata` (dict): Policy-specific metadata

**Raises:**
- `ValueError`: If moral_value not in [0.0, 1.0]

**Example:**
```python
result = wrapper.generate(
    prompt="Explain quantum computing",
    moral_value=0.9,
    context_top_k=10
)

if result["accepted"]:
    print(result["response"])
else:
    print(f"Rejected: {result['note']}")
```

#### get_state

Get current system state.

```python
def get_state() -> dict
```

**Returns:** Dictionary with keys:
- `step` (int): Current step counter
- `phase` (str): Current phase
- `phase_counter` (int): Counter within current phase
- `moral_threshold` (float): Current moral threshold
- `moral_ema` (float): Exponential moving average of acceptance rate
- `accepted_count` (int): Total accepted requests
- `rejected_count` (int): Total rejected requests
- `qilm_stats` (dict): QILM memory statistics
  - `capacity` (int): Maximum capacity
  - `used` (int): Current usage
  - `memory_mb` (float): Memory usage in MB
- `synaptic_norms` (dict): Synaptic memory L2 norms
  - `L1` (float): L1 layer norm
  - `L2` (float): L2 layer norm
  - `L3` (float): L3 layer norm

**Example:**
```python
state = wrapper.get_state()
print(f"Phase: {state['phase']}, Step: {state['step']}")
print(f"Memory: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")
print(f"Moral threshold: {state['moral_threshold']:.2f}")
```

#### reset

Reset system state (primarily for testing).

```python
def reset() -> None
```

**Example:**
```python
wrapper.reset()
```

---

## Speech Governance

The Speech Governance system provides a pluggable framework for applying arbitrary linguistic policies to LLM outputs. Speech governors can implement content filtering, style enforcement, grammar correction, or any other text transformation policy.

### SpeechGovernor Protocol

A speech governor is any callable that implements the following protocol:

```python
from mlsdm.speech.governance import SpeechGovernor, SpeechGovernanceResult

class MyGovernor:
    def __call__(
        self,
        *,
        prompt: str,
        draft: str,
        max_tokens: int
    ) -> SpeechGovernanceResult:
        # Analyze and potentially modify draft
        final_text = self.process(draft)

        return SpeechGovernanceResult(
            final_text=final_text,
            raw_text=draft,
            metadata={"custom_key": "custom_value"}
        )
```

**Parameters:**
- `prompt` (str): Original user prompt
- `draft` (str): Raw LLM-generated text before governance
- `max_tokens` (int): Maximum tokens requested for generation

**Returns:** `SpeechGovernanceResult` with:
- `final_text` (str): Final text after policy application
- `raw_text` (str): Original draft text
- `metadata` (dict): Policy-specific information

### Example: Simple Content Filter

```python
from mlsdm.speech.governance import SpeechGovernanceResult

class ContentFilter:
    def __init__(self, forbidden_words: list[str]):
        self.forbidden = set(forbidden_words)

    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        words = draft.split()
        filtered = [w for w in words if w.lower() not in self.forbidden]
        final = " ".join(filtered)

        return SpeechGovernanceResult(
            final_text=final,
            raw_text=draft,
            metadata={"words_filtered": len(words) - len(filtered)}
        )

# Use with LLMWrapper
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    speech_governor=ContentFilter(["spam", "toxic"])
)
```

### Example: Style Enforcement

```python
class FormalStyleGovernor:
    def __call__(self, *, prompt: str, draft: str, max_tokens: int) -> SpeechGovernanceResult:
        # Replace informal contractions
        formal = draft.replace("don't", "do not").replace("can't", "cannot")

        return SpeechGovernanceResult(
            final_text=formal,
            raw_text=draft,
            metadata={"style": "formal"}
        )
```

### AphasiaSpeechGovernor

Built-in governor for detecting and repairing telegraphic speech patterns (Broca's aphasia):

```python
from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector, AphasiaSpeechGovernor

detector = AphasiaBrocaDetector(
    min_sentence_len=6.0,
    min_function_word_ratio=0.15,
    max_fragment_ratio=0.5
)

aphasia_governor = AphasiaSpeechGovernor(
    detector=detector,
    repair_enabled=True,
    severity_threshold=0.3,
    llm_generate_fn=my_llm  # LLM for repair
)

wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    speech_governor=aphasia_governor
)
```

**AphasiaSpeechGovernor Parameters:**
- `detector` (AphasiaBrocaDetector): Detector instance
- `repair_enabled` (bool): Whether to repair detected aphasia
- `severity_threshold` (float): Minimum severity to trigger repair (0.0-1.0)
- `llm_generate_fn` (Callable): LLM function for repair (required if repair_enabled)

**Metadata Keys:**
- `aphasia_report` (dict): Detection results
  - `is_aphasic` (bool): Whether aphasia detected
  - `severity` (float): Severity score (0.0-1.0)
  - `flags` (list): Specific issues detected
- `repaired` (bool): Whether text was repaired

### PipelineSpeechGovernor

**New in v1.3.0**: Compose multiple speech governors into a deterministic pipeline with failure isolation.

```python
from mlsdm.speech.governance import PipelineSpeechGovernor
from mlsdm.extensions.neuro_lang_extension import AphasiaSpeechGovernor

# Create individual governors
aphasia_governor = AphasiaSpeechGovernor(...)
style_governor = FormalStyleGovernor()
length_governor = LengthControlGovernor(max_length=500)

# Compose into pipeline
pipeline = PipelineSpeechGovernor(
    governors=[
        ("aphasia_broca", aphasia_governor),
        ("style_normalizer", style_governor),
        ("length_control", length_governor),
    ]
)

# Use with LLMWrapper
wrapper = LLMWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    speech_governor=pipeline
)
```

#### Pipeline Behavior

1. **Deterministic Execution**: Governors execute in the specified order
2. **Chained Processing**: Each governor receives the output of the previous one
3. **Failure Isolation**: If a governor raises an exception:
   - Error is logged to `mlsdm.speech.pipeline` logger
   - Governor is skipped
   - Pipeline continues with unchanged text
   - Error details recorded in metadata
4. **Metadata Preservation**: All intermediate results are recorded

#### Response Format

When using `PipelineSpeechGovernor`, the `speech_governance` key contains:

```json
{
  "speech_governance": {
    "raw_text": "original LLM draft",
    "metadata": {
      "pipeline": [
        {
          "name": "aphasia_broca",
          "status": "ok",
          "raw_text": "text before this step",
          "final_text": "text after this step",
          "metadata": {
            "aphasia_report": {...},
            "repaired": true
          }
        },
        {
          "name": "style_normalizer",
          "status": "ok",
          "raw_text": "text from previous step",
          "final_text": "normalized text",
          "metadata": {"style": "formal"}
        },
        {
          "name": "failing_governor",
          "status": "error",
          "error_type": "RuntimeError",
          "error_message": "error details"
        }
      ]
    }
  }
}
```

#### Adding New Governors to Pipeline

To extend the pipeline without modifying core code:

```python
# Define custom governor
class ToxicityGovernor:
    def __call__(self, *, prompt: str, draft: str, max_tokens: int):
        score = self.check_toxicity(draft)
        if score > 0.7:
            clean_text = self.detoxify(draft)
        else:
            clean_text = draft

        return SpeechGovernanceResult(
            final_text=clean_text,
            raw_text=draft,
            metadata={"toxicity_score": score}
        )

# Add to pipeline
pipeline = PipelineSpeechGovernor(
    governors=[
        ("aphasia_broca", aphasia_governor),
        ("toxicity_filter", ToxicityGovernor()),
        ("style_normalizer", style_governor),
    ]
)
```

### Design Principles

1. **Single Responsibility**: Each governor implements one policy
2. **Composability**: Multiple policies can be chained via `PipelineSpeechGovernor`
3. **Observable**: Metadata provides transparency for each step
4. **Non-Invasive**: Governor is optional; LLMWrapper works without it
5. **Testable**: Pure functions enable isolated testing
6. **Failure Isolation**: Pipeline continues even if individual governors fail

---

## NeuroLangWrapper

Extended LLM wrapper with NeuroLang + Aphasia-Broca detection and repair capabilities.

### Constructor

```python
NeuroLangWrapper(
    llm_generate_fn: Callable[[str, int], str],
    embedding_fn: Callable[[str], np.ndarray],
    dim: int = 384,
    capacity: int = 20000,
    wake_duration: int = 8,
    sleep_duration: int = 3,
    initial_moral_threshold: float = 0.50,
    aphasia_detect_enabled: bool = True,
    aphasia_repair_enabled: bool = True,
    aphasia_severity_threshold: float = 0.3
)
```

**Parameters:**

All parameters from `LLMWrapper`, plus:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aphasia_detect_enabled` | bool | True | Enable/disable Aphasia-Broca detection |
| `aphasia_repair_enabled` | bool | True | Enable/disable automatic repair of detected aphasia |
| `aphasia_severity_threshold` | float | 0.3 | Minimum severity (0.0-1.0) to trigger repair |

**Raises:**
- `ValueError`: If parameters are invalid

**Example:**
```python
from mlsdm.extensions import NeuroLangWrapper
import numpy as np

def my_llm(prompt: str, max_tokens: int) -> str:
    return "Generated response"

def my_embed(text: str) -> np.ndarray:
    return np.random.randn(384).astype(np.float32)

# Full detection + repair (default)
wrapper = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    dim=384,
    aphasia_detect_enabled=True,
    aphasia_repair_enabled=True,
    aphasia_severity_threshold=0.3
)

# Monitoring only (detect but don't repair)
wrapper_monitor = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    dim=384,
    aphasia_detect_enabled=True,
    aphasia_repair_enabled=False
)

# Detection disabled
wrapper_disabled = NeuroLangWrapper(
    llm_generate_fn=my_llm,
    embedding_fn=my_embed,
    dim=384,
    aphasia_detect_enabled=False
)
```

### Methods

#### generate

Generate text with cognitive governance and Aphasia-Broca detection/repair.

```python
def generate(
    prompt: str,
    moral_value: float = 0.5,
    max_tokens: int = 50
) -> dict
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `prompt` | str | Required | Input prompt text |
| `moral_value` | float | 0.5 | Moral acceptability score (0.0-1.0) |
| `max_tokens` | int | 50 | Maximum tokens for generation |

**Returns:** Dictionary with keys:
- `response` (str): Generated (and possibly repaired) text
- `accepted` (bool): Whether request was accepted by moral filter
- `phase` (str): Current phase ("wake" or "sleep")
- `neuro_enhancement` (str): NeuroLang processing result
- `aphasia_flags` (dict or None): Aphasia detection report (None if detection disabled)
  - `is_aphasic` (bool): Whether text shows aphasia symptoms
  - `severity` (float): Severity score (0.0-1.0)
  - `avg_sentence_len` (float): Average sentence length
  - `function_word_ratio` (float): Ratio of function words
  - `fragment_ratio` (float): Ratio of sentence fragments
  - `flags` (list): List of specific issues detected

**Behavior based on configuration:**

1. **Detection disabled** (`aphasia_detect_enabled=False`):
   - Returns base LLM response without analysis
   - `aphasia_flags` will be `None`

2. **Detection enabled, repair disabled** (`aphasia_detect_enabled=True`, `aphasia_repair_enabled=False`):
   - Analyzes response and includes `aphasia_flags`
   - Does not modify response text (monitoring mode)

3. **Both enabled** (default):
   - Analyzes response
   - Repairs if `is_aphasic=True` and `severity >= aphasia_severity_threshold`
   - Always includes final `aphasia_flags` (reflects original analysis)

**Example:**
```python
# Full detection + repair
result = wrapper.generate(
    prompt="Explain the system",
    moral_value=0.8,
    max_tokens=100
)

if result["accepted"]:
    print(result["response"])
    if result["aphasia_flags"]:
        print(f"Aphasia detected: {result['aphasia_flags']['is_aphasic']}")
        print(f"Severity: {result['aphasia_flags']['severity']:.2f}")
```

---

## CognitiveController

Low-level cognitive controller for direct memory operations.

### Constructor

```python
CognitiveController(dim: int = 384, capacity: int = 20000)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `dim` | int | 384 | Vector dimension |
| `capacity` | int | 20000 | Memory capacity |

### Methods

#### process_event

Process a single event vector.

```python
def process_event(
    event_vector: np.ndarray,
    moral_value: float
) -> dict
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `event_vector` | np.ndarray | Event vector of shape (dim,), normalized |
| `moral_value` | float | Moral value (0.0-1.0) |

**Returns:** Dictionary with processing state

**Raises:**
- `ValueError`: If event_vector has wrong shape or moral_value invalid

**Example:**
```python
from mlsdm.core.cognitive_controller import CognitiveController
import numpy as np

controller = CognitiveController(dim=384)
vector = np.random.randn(384).astype(np.float32)
vector = vector / np.linalg.norm(vector)

state = controller.process_event(vector, moral_value=0.8)
print(state)
```

#### retrieve_context

Retrieve relevant context vectors from memory.

```python
def retrieve_context(
    query_vector: np.ndarray,
    top_k: int = 5
) -> List[np.ndarray]
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query_vector` | np.ndarray | Required | Query vector for retrieval |
| `top_k` | int | 5 | Number of vectors to retrieve |

**Returns:** List of retrieved vectors (up to top_k)

---

## Memory Components

### PELM

Phase-Entangled Lattice Memory with phase entanglement.

#### Constructor

```python
PELM(dim: int, capacity: int = 20000)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `dim` | int | Required | Vector dimension |
| `capacity` | int | 20000 | Maximum capacity |

#### Methods

##### entangle_phase

Store vector with phase entanglement.

```python
def entangle_phase(
    event_vector: np.ndarray,
    phase: float
) -> None
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `event_vector` | np.ndarray | Vector to store (dim,) |
| `phase` | float | Phase value for entanglement |

##### retrieve

Retrieve vectors by phase similarity.

```python
def retrieve(
    phase: float,
    tolerance: float = 0.2,
    top_k: int = 5
) -> List[np.ndarray]
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `phase` | float | Required | Target phase |
| `tolerance` | float | 0.2 | Phase tolerance |
| `top_k` | int | 5 | Max results |

**Returns:** List of retrieved vectors

---

### MultiLevelSynapticMemory

Three-level synaptic memory with differential decay.

#### Constructor

```python
MultiLevelSynapticMemory(
    dim: int,
    lambda_l1: float = 0.50,
    lambda_l2: float = 0.10,
    lambda_l3: float = 0.01
)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `dim` | int | Required | Vector dimension |
| `lambda_l1` | float | 0.50 | L1 decay rate (fast) |
| `lambda_l2` | float | 0.10 | L2 decay rate (medium) |
| `lambda_l3` | float | 0.01 | L3 decay rate (slow) |

#### Methods

##### update

Update memory with new event.

```python
def update(event_vector: np.ndarray) -> None
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `event_vector` | np.ndarray | Event vector to integrate |

##### get_state

Get current memory state.

```python
def get_state() -> dict
```

**Returns:** Dictionary with L1, L2, L3 vectors and norms

---

## Filtering Components

### MoralFilterV2

Adaptive moral filter with homeostatic threshold.

#### Constructor

```python
MoralFilterV2(
    initial_threshold: float = 0.50,
    adapt_rate: float = 0.05,
    ema_alpha: float = 0.1
)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `initial_threshold` | float | 0.50 | Starting threshold (0.30-0.90) |
| `adapt_rate` | float | 0.05 | Adaptation step size |
| `ema_alpha` | float | 0.1 | EMA smoothing factor |

#### Methods

##### evaluate

Evaluate if moral value passes threshold.

```python
def evaluate(moral_value: float) -> bool
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `moral_value` | float | Moral score (0.0-1.0) |

**Returns:** True if accepted, False if rejected

##### adapt

Adapt threshold based on acceptance.

```python
def adapt(accepted: bool) -> None
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `accepted` | bool | Whether last evaluation was accepted |

**Example:**
```python
from mlsdm.cognition.moral_filter_v2 import MoralFilterV2

filter = MoralFilterV2(0.5)
accepted = filter.evaluate(0.8)
filter.adapt(accepted)
```

---

### OntologyMatcher

Semantic ontology matching with multiple metrics.

#### Constructor

```python
OntologyMatcher(
    ontology_vectors: np.ndarray,
    labels: List[str]
)
```

**Parameters:**

| Name | Type | Description |
|------|------|-------------|
| `ontology_vectors` | np.ndarray | Ontology vectors (n_concepts, dim) |
| `labels` | List[str] | Concept labels |

#### Methods

##### match

Find best matching ontology concept.

```python
def match(
    event_vector: np.ndarray,
    metric: str = "cosine"
) -> Tuple[str, float]
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `event_vector` | np.ndarray | Required | Query vector |
| `metric` | str | "cosine" | Distance metric ("cosine" or "euclidean") |

**Returns:** Tuple of (label, score)

---

## Rhythm Components

### CognitiveRhythm

Wake/sleep cycle management.

#### Constructor

```python
CognitiveRhythm(
    wake_duration: int = 8,
    sleep_duration: int = 3
)
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `wake_duration` | int | 8 | Wake phase steps |
| `sleep_duration` | int | 3 | Sleep phase steps |

#### Methods

##### step

Advance one step and get current phase.

```python
def step() -> str
```

**Returns:** Current phase ("wake" or "sleep")

##### get_phase_value

Get numerical phase value for memory entanglement.

```python
def get_phase_value() -> float
```

**Returns:** 0.1 (wake) or 0.9 (sleep)

---

## Utilities

### MetricsCollector

Performance and behavior metrics collection.

#### Methods

##### record_event_processing

Record event processing time.

```python
def record_event_processing(duration_ms: float) -> None
```

##### get_statistics

Get collected statistics.

```python
def get_statistics() -> dict
```

**Returns:** Dictionary with metrics

---

## Type Definitions

### Common Types

```python
from typing import Callable, Optional, List, Tuple, Dict
import numpy as np

# LLM generation function type
LLMGenerateFn = Callable[[str, int], str]

# Embedding function type
EmbeddingFn = Callable[[str], np.ndarray]

# State dictionary type
State = Dict[str, Any]
```

---

## Error Handling

### Common Exceptions

- `ValueError`: Invalid input parameters
- `RuntimeError`: System state errors
- `TypeError`: Type mismatches

### Error Examples

```python
# Invalid moral value
try:
    result = wrapper.generate("Hello", moral_value=1.5)
except ValueError as e:
    print(f"Invalid moral value: {e}")

# Invalid vector dimension
try:
    vector = np.random.randn(512)  # Wrong dimension
    controller.process_event(vector, 0.8)
except ValueError as e:
    print(f"Dimension mismatch: {e}")
```

---

## Performance Characteristics

### Latency

- **process_event**: ~2ms (P50), ~10ms (P95)
- **retrieve_context**: ~5-15ms depending on top_k
- **generate**: Depends on LLM + overhead (~2-20ms)

### Memory

- **PELM**: Fixed allocation (capacity × dim × 4 bytes)
- **Example**: 20,000 × 384 × 4 = 29.37 MB
- **Total system**: ~30 MB (well under 1.4 GB limit)

### Concurrency

- Thread-safe with internal locking
- Tested at 1000+ concurrent requests
- No lost updates or race conditions

---

## Examples

### Complete Integration Example

```python
from mlsdm.core.llm_wrapper import LLMWrapper
import numpy as np
import openai

# Setup OpenAI
openai.api_key = "your-key"

def openai_gen(prompt: str, max_tokens: int) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def simple_embed(text: str) -> np.ndarray:
    # Replace with actual embeddings
    return np.random.randn(384).astype(np.float32)

# Create wrapper
wrapper = LLMWrapper(
    llm_generate_fn=openai_gen,
    embedding_fn=simple_embed,
    dim=384,
    capacity=20000
)

# Generate with governance
result = wrapper.generate(
    prompt="What is artificial intelligence?",
    moral_value=0.9
)

if result["accepted"]:
    print(f"Response: {result['response']}")
    print(f"Phase: {result['phase']}")
    print(f"Context items: {result['context_items']}")
else:
    print(f"Rejected: {result['note']}")

# Check system state
state = wrapper.get_state()
print(f"\nSystem State:")
print(f"  Steps: {state['step']}")
print(f"  Phase: {state['phase']}")
print(f"  Memory: {state['qilm_stats']['used']}/{state['qilm_stats']['capacity']}")
print(f"  Moral threshold: {state['moral_threshold']:.2f}")
```

---

## See Also

- [README.md](README.md) - Project overview
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - Usage examples
- [ARCHITECTURE_SPEC.md](ARCHITECTURE_SPEC.md) - Architecture details
- [examples/](examples/) - Code examples

---

**Version**: 1.0.0
**Last Updated**: November 2025
**Maintainer**: neuron7x
