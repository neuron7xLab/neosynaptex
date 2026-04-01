# MyceliumFractalNet Integration Connectors & Publishers Guide

**Version**: 1.0.0  
**Date**: 2025-12-04  
**Target**: MyceliumFractalNet v4.1

---

## Overview

This guide describes the upstream connectors and downstream publishers for integrating MyceliumFractalNet with external systems. These components enable MFN to operate as part of a larger data processing pipeline.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
├──────────────┬───────────────┬──────────────────────────────────┤
│  REST APIs   │  File Feeds   │  Kafka Topics                    │
└──────────────┴───────────────┴──────────────────────────────────┘
        │               │                      │
        ▼               ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│            Upstream Connectors (Data Ingestion)                  │
├──────────────┬───────────────┬──────────────────────────────────┤
│ RESTConnector│ FileConnector │ KafkaConnectorAdapter            │
└──────────────┴───────────────┴──────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  MyceliumFractalNet Engine    │
        │  - Simulation                 │
        │  - Feature Extraction         │
        │  - Processing                 │
        └───────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│          Downstream Publishers (Data Publication)                │
├──────────────┬────────────────┬─────────────────────────────────┤
│WebhookPublish│ FilePublisher  │ KafkaPublisherAdapter           │
└──────────────┴────────────────┴─────────────────────────────────┘
        │               │                      │
        ▼               ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  External Data Consumers                         │
├──────────────┬────────────────┬─────────────────────────────────┤
│   Webhooks   │  File Storage  │  Kafka Topics                   │
└──────────────┴────────────────┴─────────────────────────────────┘
```

---

## Upstream Connectors

Upstream connectors pull data from external sources for processing by MFN.

### RESTConnector

HTTP API connector for pulling data via REST endpoints.

#### Features
- GET/POST HTTP requests
- Custom headers and authentication
- Automatic retry with exponential backoff
- Request/response logging
- Metrics tracking

#### Installation
```bash
pip install aiohttp
```

#### Usage Example

```python
from mycelium_fractal_net.integration import RESTConnector, ConnectorConfig

# Create connector with configuration
config = ConnectorConfig(
    max_retries=3,
    initial_retry_delay=1.0,
    timeout=30.0,
)

connector = RESTConnector(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer TOKEN"},
    config=config,
)

# Connect and fetch data
await connector.connect()
data = await connector.fetch(
    endpoint="/data/latest",
    method="GET",
    params={"limit": 100},
)
await connector.disconnect()

# Check metrics
print(f"Success rate: {connector.metrics.to_dict()['success_rate']:.2%}")
```

#### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | required | Base URL for API |
| `headers` | dict | {} | HTTP headers for all requests |
| `config.max_retries` | int | 3 | Maximum retry attempts |
| `config.retry_strategy` | enum | EXPONENTIAL_BACKOFF | Retry strategy |
| `config.initial_retry_delay` | float | 1.0 | Initial retry delay (seconds) |
| `config.max_retry_delay` | float | 60.0 | Maximum retry delay (seconds) |
| `config.timeout` | float | 30.0 | Request timeout (seconds) |

---

### FileConnector

File-based connector for processing files from a directory.

#### Features
- Directory polling for new files
- Glob pattern matching (*.json, *.csv, etc.)
- Automatic file cleanup option
- File tracking to avoid reprocessing
- No external dependencies

#### Usage Example

```python
from mycelium_fractal_net.integration import FileConnector, ConnectorConfig

# Create connector
config = ConnectorConfig()
connector = FileConnector(
    directory="/data/input",
    pattern="*.json",
    auto_delete=True,  # Delete files after processing
    config=config,
)

# Connect and process files
await connector.connect()

while True:
    data = await connector.fetch()
    if data is None:
        break  # No more files
    
    # Process data...
    print(f"Processed: {data}")

await connector.disconnect()
```

#### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | str/Path | required | Directory to watch |
| `pattern` | str | "*.json" | Glob pattern for files |
| `auto_delete` | bool | False | Delete files after processing |

---

### KafkaConnectorAdapter

Kafka consumer for reading messages from Kafka topics.

#### Features
- Multiple topic subscription
- Consumer group management
- Automatic offset commit
- Message deserialization
- Batch fetching

#### Installation
```bash
pip install kafka-python
```

#### Usage Example

```python
from mycelium_fractal_net.integration import KafkaConnectorAdapter, ConnectorConfig

# Create connector
config = ConnectorConfig()
connector = KafkaConnectorAdapter(
    bootstrap_servers=["localhost:9092"],
    topics=["mfn-input", "data-stream"],
    group_id="mfn-processor",
    config=config,
)

# Connect and consume messages
await connector.connect()

messages = await connector.fetch(max_messages=100, timeout_ms=1000)
for msg in messages:
    # Process message...
    print(f"Received: {msg}")

await connector.disconnect()
```

#### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bootstrap_servers` | list | required | Kafka broker addresses |
| `topics` | list | required | Topics to subscribe to |
| `group_id` | str | required | Consumer group ID |
| `max_messages` | int | 100 | Max messages per fetch |
| `timeout_ms` | int | 1000 | Poll timeout (milliseconds) |

---

## Downstream Publishers

Downstream publishers send MFN results to external systems.

### WebhookPublisher

HTTP POST publisher for sending data to webhook endpoints.

#### Features
- JSON payload serialization
- Custom headers and authentication
- Automatic retry with exponential backoff
- Request/response logging
- Metrics tracking

#### Installation
```bash
pip install aiohttp
```

#### Usage Example

```python
from mycelium_fractal_net.integration import WebhookPublisher, PublisherConfig

# Create publisher
config = PublisherConfig(max_retries=3)
publisher = WebhookPublisher(
    webhook_url="https://api.example.com/webhook",
    headers={"Authorization": "Bearer TOKEN"},
    config=config,
)

# Connect and publish
await publisher.connect()

result = {
    "event": "simulation_complete",
    "fractal_dimension": 1.584,
    "features": [/* 18 features */],
}

await publisher.publish(result)
await publisher.disconnect()

# Check metrics
print(f"Published: {publisher.metrics.successful_publishes}")
```

---

### KafkaPublisherAdapter

Kafka producer for publishing messages to Kafka topics.

#### Features
- Topic publishing
- Message serialization
- Delivery acknowledgment
- Batch publishing support
- Configurable delivery guarantees

#### Installation
```bash
pip install kafka-python
```

#### Usage Example

```python
from mycelium_fractal_net.integration import KafkaPublisherAdapter, PublisherConfig

# Create publisher
config = PublisherConfig()
publisher = KafkaPublisherAdapter(
    bootstrap_servers=["localhost:9092"],
    topic="mfn-output",
    config=config,
)

# Connect and publish
await publisher.connect()

result = {
    "simulation_id": "sim-12345",
    "fractal_features": {/* features */},
}

await publisher.publish(result)
await publisher.disconnect()
```

---

### FilePublisher

File-based publisher for writing data to files.

#### Features
- JSON file output
- Append and overwrite modes
- Automatic directory creation
- File rotation support
- No external dependencies

#### Usage Example

```python
from mycelium_fractal_net.integration import FilePublisher, PublisherConfig

# Create publisher
config = PublisherConfig()
publisher = FilePublisher(
    directory="/data/output",
    filename_pattern="result_{timestamp}.json",
    append_mode=False,
    config=config,
)

# Connect and publish
await publisher.connect()

result = {
    "simulation_complete": True,
    "metrics": {/* metrics */},
}

await publisher.publish(result)
await publisher.disconnect()
```

#### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | str/Path | required | Output directory |
| `filename_pattern` | str | "output_{timestamp}.json" | Filename pattern |
| `append_mode` | bool | False | Append to existing file |

---

## Retry Strategies

All connectors and publishers support configurable retry strategies:

### Exponential Backoff (Default)
Doubles delay after each retry: 1s → 2s → 4s → 8s → ...

```python
config = ConnectorConfig(
    retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_retry_delay=1.0,
    max_retry_delay=60.0,
)
```

### Linear Backoff
Increases delay linearly: 2s → 4s → 6s → 8s → ...

```python
config = ConnectorConfig(
    retry_strategy=RetryStrategy.LINEAR_BACKOFF,
    initial_retry_delay=2.0,
)
```

### Fixed Delay
Uses same delay for all retries: 3s → 3s → 3s → ...

```python
config = ConnectorConfig(
    retry_strategy=RetryStrategy.FIXED_DELAY,
    initial_retry_delay=3.0,
)
```

### No Retry
Fails immediately without retrying.

```python
config = ConnectorConfig(
    retry_strategy=RetryStrategy.NO_RETRY,
)
```

---

## Metrics Tracking

All components track operational metrics:

```python
# Access metrics
metrics = connector.metrics.to_dict()

print(f"Total requests: {metrics['total_requests']}")
print(f"Successful: {metrics['successful_requests']}")
print(f"Failed: {metrics['failed_requests']}")
print(f"Success rate: {metrics['success_rate']:.2%}")
print(f"Total bytes: {metrics['total_bytes_fetched']}")
print(f"Total retries: {metrics['total_retries']}")
```

### Metrics Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_requests` | int | Total operations attempted |
| `successful_requests` | int | Successful operations |
| `failed_requests` | int | Failed operations |
| `total_retries` | int | Total retry attempts |
| `total_bytes_fetched` | int | Total bytes processed |
| `last_fetch_timestamp` | float | Timestamp of last operation |
| `last_error` | str | Last error message |
| `last_error_timestamp` | float | Timestamp of last error |
| `success_rate` | float | Success rate (0.0-1.0) |

---

## Error Handling

### Automatic Retry
Components automatically retry failed operations according to the configured retry strategy.

### Error Logging
All errors are logged with structured context:

```python
logger.error(
    "Operation failed after 3 retries",
    extra={
        "operation": "REST GET /data",
        "max_retries": 3,
        "error": "Connection timeout",
    },
    exc_info=True,
)
```

### Exception Propagation
After exhausting all retries, the original exception is raised to the caller.

---

## Complete Integration Example

```python
import asyncio
from mycelium_fractal_net.integration import (
    RESTConnector,
    WebhookPublisher,
    ConnectorConfig,
    PublisherConfig,
)
from mycelium_fractal_net import run_mycelium_simulation_with_history

async def process_pipeline():
    # Setup connector
    connector_config = ConnectorConfig(max_retries=3)
    connector = RESTConnector(
        base_url="https://api.example.com",
        config=connector_config,
    )
    
    # Setup publisher
    publisher_config = PublisherConfig(max_retries=3)
    publisher = WebhookPublisher(
        webhook_url="https://results.example.com/webhook",
        config=publisher_config,
    )
    
    await connector.connect()
    await publisher.connect()
    
    try:
        # Fetch input parameters
        params = await connector.fetch(endpoint="/parameters")
        
        # Run MFN simulation
        result = run_mycelium_simulation_with_history({
            "grid_size": params["grid_size"],
            "steps": params["steps"],
            "seed": params["seed"],
        })
        
        # Publish results
        await publisher.publish({
            "simulation_id": params["id"],
            "fractal_dimension": result["fractal_dimension"],
            "features": result["features"],
        })
        
        print(f"Pipeline complete!")
        print(f"Connector metrics: {connector.metrics.to_dict()}")
        print(f"Publisher metrics: {publisher.metrics.to_dict()}")
        
    finally:
        await connector.disconnect()
        await publisher.disconnect()

# Run pipeline
asyncio.run(process_pipeline())
```

---

## Testing

Run integration tests:

```bash
# Run all integration tests
pytest tests/integration/test_connectors.py tests/integration/test_publishers.py -v

# Run specific connector tests
pytest tests/integration/test_connectors.py::TestFileConnector -v

# Run with coverage
pytest tests/integration/ --cov=mycelium_fractal_net.integration --cov-report=html
```

---

## Best Practices

1. **Connection Management**: Always use try/finally blocks or context managers to ensure proper cleanup.

2. **Retry Configuration**: Choose appropriate retry strategies based on the external system:
   - Use exponential backoff for rate-limited APIs
   - Use fixed delay for transient network issues
   - Use no retry for operations that should fail fast

3. **Metrics Monitoring**: Regularly check metrics to identify connectivity issues or performance degradation.

4. **Error Handling**: Log all errors with sufficient context for debugging.

5. **Resource Limits**: Configure appropriate timeouts and max_retries to prevent hanging operations.

6. **Testing**: Test connectors/publishers with mock external systems before deploying to production.

---

## Troubleshooting

### Connection Timeouts
- Increase `timeout` parameter
- Check network connectivity
- Verify external service is responsive

### High Retry Counts
- Review external service availability
- Adjust retry strategy
- Increase initial_retry_delay

### Memory Issues
- Process data in batches
- Implement periodic cleanup
- Monitor metrics.total_bytes_fetched

### Import Errors
- Install required dependencies: `pip install aiohttp kafka-python`
- Check Python version compatibility (>=3.10)

---

## References

- [MFN Integration Gaps](MFN_INTEGRATION_GAPS.md)
- [MFN System Role](MFN_SYSTEM_ROLE.md)
- [MFN Architecture](ARCHITECTURE.md)
- [Security Documentation](MFN_SECURITY.md)

---

*Last updated: 2025-12-04*  
*Author: MFN Integration Team*
