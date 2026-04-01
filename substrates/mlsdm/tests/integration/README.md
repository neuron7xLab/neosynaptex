# Integration Tests

This directory contains integration tests for the MLSDM system with real-world LLM APIs and scenarios.

## test_real_llm.py

Comprehensive integration tests for LLM APIs including:

### OpenAI API Integration
- Basic API calls with mock client
- Rate limit handling with retry logic
- Timeout error handling
- Authentication error handling

### Local Model Integration (Ollama/llama.cpp style)
- Mock local model integration
- Latency measurement
- Memory efficiency verification

### Anthropic Claude API Integration
- Basic Claude API calls
- Service overload handling
- Mock streaming responses

### Latency Distribution Testing
- Measurement of P50/P95/P99 latencies
- Latency behavior under load

### Moral Filter with Toxic Inputs
- Toxicity rejection testing (simulated HateSpeech dataset)
- Moral filter adaptation
- Statistics collection

## Running Tests

```bash
# Run all integration tests
pytest tests/integration/test_real_llm.py -v

# Run specific test class
pytest tests/integration/test_real_llm.py::TestOpenAIIntegration -v

# Run with output
pytest tests/integration/test_real_llm.py -v -s
```

## Test Coverage

The tests verify:
- ✅ Error handling for API failures
- ✅ Retry mechanisms for transient errors
- ✅ Latency characteristics
- ✅ Memory bounds under load
- ✅ Moral filtering effectiveness
- ✅ Response quality and coherence

## Dependencies

Required packages:
- pytest
- pytest-asyncio
- numpy
- unittest.mock (standard library)

Optional for real API testing (not used by default):
- openai
- anthropic
