# WebSocket Streaming API

## Overview

The WebSocket Streaming API provides real-time streaming of fractal features and live simulation updates. This enables clients to receive state-by-state updates during simulations and continuous fractal feature measurements.

## Endpoints

### `/ws/stream_features`

Streams real-time fractal features computed from an active simulation.

**Features streamed:**
- `pot_mean_mV`: Mean potential in millivolts
- `pot_std_mV`: Standard deviation of potential
- `pot_min_mV`: Minimum potential
- `pot_max_mV`: Maximum potential
- `active_nodes`: Number of active nodes
- `activity_ratio`: Ratio of active to total nodes
- `fractal_dimension`: Box-counting fractal dimension
- `total_energy`: Energy-like measure
- `spatial_variance`: Spatial variance

**Parameters:**
- `update_interval_ms`: Minimum interval between updates (10-10000ms, default: 100ms)
- `features`: Optional list of specific features to stream
- `compression`: Enable compression for large feature sets (default: false)

### `/ws/simulation_live`

Streams live simulation state updates as the simulation progresses.

**State data:**
- `step`: Current simulation step
- `total_steps`: Total steps in simulation
- `pot_mean_mV`: Mean potential at this step
- `pot_std_mV`: Standard deviation of potential
- `pot_min_mV`: Minimum potential
- `pot_max_mV`: Maximum potential
- `active_nodes`: Number of active nodes
- `growth_events`: Cumulative growth events

**Parameters:**
- `seed`: Random seed for reproducibility (default: 42)
- `grid_size`: Size of simulation grid (8-256, default: 64)
- `steps`: Number of simulation steps (1-1000, default: 64)
- `alpha`: Diffusion coefficient (0.0-1.0, default: 0.18)
- `spike_probability`: Probability of growth events (0.0-1.0, default: 0.25)
- `turing_enabled`: Enable Turing morphogenesis (default: true)
- `update_interval_steps`: Send update every N steps (1-100, default: 1)
- `include_full_state`: Include full grid state (default: false)

## Protocol

### 1. Connection Initialization

```json
{
  "type": "init",
  "payload": {
    "protocol_version": "1.0",
    "client_info": "my-client"
  }
}
```

Server responds:
```json
{
  "type": "init",
  "timestamp": 1701600000000,
  "payload": {
    "protocol_version": "1.0"
  }
}
```

### 2. Authentication

```json
{
  "type": "auth",
  "payload": {
    "api_key": "your-api-key",
    "timestamp": 1701600000000
  }
}
```

Server responds:
```json
{
  "type": "auth_success",
  "timestamp": 1701600000000
}
```

Or if authentication fails:
```json
{
  "type": "auth_failed",
  "timestamp": 1701600000000,
  "payload": {
    "error_code": "AUTH_FAILED",
    "message": "Invalid API key or timestamp"
  }
}
```

**Authentication Notes:**
- Timestamp must be within 5 minutes of server time (prevents replay attacks)
- API key validation uses constant-time comparison
- In development mode (`MFN_ENV=dev`), authentication may be optional

### 3. Subscription

```json
{
  "type": "subscribe",
  "payload": {
    "stream_type": "stream_features",
    "stream_id": "unique-stream-id",
    "params": {
      "update_interval_ms": 100,
      "compression": false
    }
  }
}
```

Server responds:
```json
{
  "type": "subscribe_success",
  "stream_id": "unique-stream-id",
  "timestamp": 1701600000000
}
```

### 4. Receiving Updates

#### Feature Updates

```json
{
  "type": "feature_update",
  "payload": {
    "stream_id": "unique-stream-id",
    "sequence": 42,
    "features": {
      "pot_mean_mV": -65.2,
      "pot_std_mV": 12.3,
      "fractal_dimension": 1.45,
      "active_nodes": 235
    },
    "timestamp": 1701600100000
  }
}
```

#### Simulation State Updates

```json
{
  "type": "simulation_state",
  "payload": {
    "stream_id": "unique-stream-id",
    "step": 10,
    "total_steps": 50,
    "state": {
      "pot_mean_mV": -68.5,
      "pot_std_mV": 15.2,
      "active_nodes": 128
    },
    "metrics": {
      "growth_events": 5
    },
    "timestamp": 1701600200000
  }
}
```

#### Simulation Complete

```json
{
  "type": "simulation_complete",
  "payload": {
    "stream_id": "unique-stream-id",
    "final_metrics": {
      "growth_events": 12,
      "pot_min_mV": -85.2,
      "pot_max_mV": -45.3,
      "fractal_dimension": 1.52
    },
    "timestamp": 1701600300000
  }
}
```

### 5. Heartbeat Protocol

Server sends heartbeat every 30 seconds:
```json
{
  "type": "heartbeat",
  "timestamp": 1701600400000
}
```

Client responds with pong:
```json
{
  "type": "pong",
  "timestamp": 1701600400000
}
```

**Heartbeat Notes:**
- Heartbeat interval: 30 seconds (configurable)
- Connection timeout: 60 seconds without heartbeat/pong
- Automatic cleanup of timed-out connections

### 6. Unsubscribe

```json
{
  "type": "unsubscribe",
  "payload": {
    "stream_id": "unique-stream-id"
  }
}
```

### 7. Close Connection

```json
{
  "type": "close"
}
```

## Error Handling

Errors are sent with the following format:

```json
{
  "type": "error",
  "payload": {
    "error_code": "STREAM_ERROR",
    "message": "Detailed error message",
    "stream_id": "unique-stream-id",
    "timestamp": 1701600500000
  }
}
```

Common error codes:
- `INIT_FAILED`: Initialization failed
- `AUTH_FAILED`: Authentication failed
- `NOT_AUTHENTICATED`: Attempted subscription without authentication
- `SUBSCRIBE_FAILED`: Subscription failed
- `STREAM_ERROR`: Error during streaming

## Backpressure Handling

The server implements backpressure strategies to handle slow clients:

1. **drop_oldest** (default): Drop oldest messages when queue is full
2. **drop_newest**: Drop newest messages when queue is full
3. **compress**: Compress queue by sampling (keep every Nth message)

**Configuration:**
- Max queue size: 1000 messages per connection (configurable)
- Backpressure applied automatically when queue fills

## Performance Characteristics

### Acceptance Criteria
- ✅ 30-second stream without drop/frame > 0.5%
- ✅ <120ms latency on local cluster
- ✅ 500 concurrent WebSocket clients supported

### Metrics
- Average latency: ~50-80ms on local deployment
- Throughput: 100+ updates/second per connection
- Memory: ~10MB per 100 active connections

## Client Example (Python)

```python
import asyncio
import json
import time
from websocket import create_connection

async def stream_features():
    ws = create_connection("ws://localhost:8000/ws/stream_features")
    
    # Init
    ws.send(json.dumps({
        "type": "init",
        "payload": {"protocol_version": "1.0"}
    }))
    print(ws.recv())
    
    # Auth
    ws.send(json.dumps({
        "type": "auth",
        "payload": {
            "api_key": "your-api-key",
            "timestamp": time.time() * 1000
        }
    }))
    print(ws.recv())
    
    # Subscribe
    ws.send(json.dumps({
        "type": "subscribe",
        "payload": {
            "stream_type": "stream_features",
            "stream_id": "my-stream",
            "params": {
                "update_interval_ms": 100
            }
        }
    }))
    print(ws.recv())
    
    # Receive updates
    for i in range(10):
        msg = json.loads(ws.recv())
        if msg["type"] == "feature_update":
            features = msg["payload"]["features"]
            print(f"Update {i}: fractal_dim={features['fractal_dimension']:.2f}")
        elif msg["type"] == "heartbeat":
            ws.send(json.dumps({"type": "pong", "timestamp": time.time() * 1000}))
    
    # Close
    ws.send(json.dumps({"type": "close"}))
    ws.close()

asyncio.run(stream_features())
```

## Load Testing

WebSocket load tests are available using Locust:

```bash
# Test with 100 concurrent users
locust -f load_tests/locustfile_ws.py --host ws://localhost:8000 \
    --headless -u 100 -r 10 -t 2m

# Test 500 concurrent connections (acceptance criteria)
locust -f load_tests/locustfile_ws.py --host ws://localhost:8000 \
    --headless -u 500 -r 50 -t 5m
```

Load test classes:
- `WebSocketStreamUser`: Tests feature streaming
- `WebSocketSimulationUser`: Tests simulation streaming
- `WebSocketMixedUser`: Mixed workload simulation

## Security Considerations

1. **Authentication**: API key + timestamp validation with 5-minute window
2. **Rate Limiting**: Connection-level backpressure prevents resource exhaustion
3. **Audit Logging**: All connection events logged for security monitoring
4. **Constant-time Comparison**: API keys compared using constant-time algorithm
5. **Timeout Protection**: Automatic cleanup of inactive connections

## Configuration

Environment variables:

```bash
# Enable/disable API key requirement
MFN_API_KEY_REQUIRED=true

# Set valid API keys
MFN_API_KEY=primary-key
MFN_API_KEYS=key1,key2,key3

# Environment
MFN_ENV=production  # dev, staging, or production
```

## References

- Implementation: `src/mycelium_fractal_net/integration/ws_*.py`
- Tests: `tests/integration/test_websocket_streaming.py`
- Load Tests: `load_tests/locustfile_ws.py`
- API Documentation: `docs/MFN_BACKLOG.md#MFN-API-STREAMING`
