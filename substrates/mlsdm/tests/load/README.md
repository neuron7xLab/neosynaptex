# Load Tests

This directory contains load testing scripts for the MLSDM system.

## Available Load Tests

| Script | Description | Dependencies |
|--------|-------------|--------------|
| `standalone_server_load_test.py` | **Self-contained server load test** | httpx |
| `locust_load_test.py` | Locust-based load testing | locust, psutil, numpy |
| `test_concurrency_core.py` | Core concurrency tests | pytest |

---

## standalone_server_load_test.py (Recommended)

**Self-contained load test that starts a server, runs tests, and generates a report.**

### Quick Start

```bash
# Basic test (10 users, 30 seconds)
python tests/load/standalone_server_load_test.py

# Custom configuration
python tests/load/standalone_server_load_test.py --users 50 --duration 60

# Test against existing server
python tests/load/standalone_server_load_test.py --host http://localhost:8000 --no-server

# Save JSON report
python tests/load/standalone_server_load_test.py --output load_report.json
```

### Features

- ✅ **Self-contained**: Automatically starts/stops MLSDM server
- ✅ **No external dependencies**: Uses only httpx (already in requirements)
- ✅ **Comprehensive metrics**: P50/P95/P99 latency, RPS, memory tracking
- ✅ **Pass/Fail criteria**: Automatic validation (>95% success, P95<500ms)
- ✅ **JSON reports**: Machine-readable output for CI integration

### Sample Output

```
======================================================================
MLSDM STANDALONE LOAD TEST REPORT
======================================================================

Test Duration: 15.2 seconds
Timestamp: 2025-12-10T12:45:48.030138

--- Request Metrics ---
Total Requests:      585
Successful Requests: 585
Failed Requests:     0
Success Rate:        100.0%
Requests/Second:     38.6

--- Latency Metrics (ms) ---
P50:  3.22
P95:  5.09
P99:  20.56
Avg:  3.43
Min:  2.00
Max:  26.26
Std:  2.29

--- Memory Metrics (MB) ---
Initial: 67.4
Final:   71.0
Growth:  3.6

--- Status ---
✅ LOAD TEST PASSED
======================================================================
```

---

## locust_load_test.py

Comprehensive load testing for MLSDM with:

### Test Configuration
- **100 concurrent users**
- **10 minute duration**
- Realistic user behavior simulation
- Multiple task types (text generation, status checks, moral filtering)

### Metrics Collected

1. **Latency Metrics**
   - P50, P95, P99 percentiles
   - Mean, min, max latency
   - Response time distribution

2. **Saturation Point Analysis**
   - RPS (Requests Per Second) capacity
   - Latency degradation detection
   - System capacity limits

3. **Memory Stability**
   - Continuous memory monitoring
   - Memory leak detection
   - Growth rate analysis

4. **Error Tracking**
   - Failed requests
   - Error types and context
   - Success rate

### Running Load Tests

#### Option 1: With Locust Web UI
```bash
locust -f tests/load/locust_load_test.py --host http://localhost:8000
# Then open http://localhost:8089 in browser
```

#### Option 2: Headless Mode (Automated)
```bash
locust -f tests/load/locust_load_test.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 600s \
  --host http://localhost:8000
```

#### Option 3: Standalone Script
```bash
python tests/load/locust_load_test.py --standalone --host http://localhost:8000
```

### Report Generation

The load test automatically generates:

1. **JSON Report**: `load_test_report.json`
   - Detailed metrics
   - Saturation analysis
   - Memory stability results
   - Error logs

2. **Console Output**
   - Real-time metrics
   - Summary statistics
   - Performance insights

### Sample Report Output

```
================================================================================
LOAD TEST REPORT
================================================================================

Test Duration: 600.0s
Total Requests: 12000
Success Rate: 99.2%

Latency Metrics:
  P50: 91.23ms
  P95: 147.45ms
  P99: 189.67ms
  Mean: 98.34ms

Saturation Analysis:
  Saturation RPS: 150
  Saturation Detected: True
  Reason: Latency spike detected

Memory Stability:
  Stable: True
  Leak Detected: False
  Initial Memory: 245.3 MB
  Final Memory: 248.7 MB
  Reason: Memory stable
================================================================================
```

## Task Sets

The load test simulates realistic user behavior:

### 1. Text Generation (60% of requests)
- Normal prompts with high moral values
- Variable content
- 100 token responses

### 2. Status Checks (20% of requests)
- Health endpoint monitoring
- System status verification

### 3. Moral Filter Testing (20% of requests)
- Variable moral values (0.3-0.7)
- Toxicity handling verification
- Shorter responses

## Dependencies

Required packages:
- locust >= 2.29.1
- psutil >= 5.9.0
- numpy

## Notes

- Ensure the MLSDM server is running before load testing
- Adjust user count and duration as needed for your requirements
- Memory monitoring runs every 5 seconds
- RPS is sampled every 1 second
- Set `MLSDM_HOST` environment variable to change target host
- Set `LOAD_TEST_OUTPUT_DIR` to change report output directory
