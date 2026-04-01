"""Example usage of the Observability Logger.

This script demonstrates how to use the observability logger
for structured JSON logging with rotation support.
"""

import tempfile
import time
from pathlib import Path

from mlsdm.observability import EventType, get_observability_logger


def main() -> None:
    """Demonstrate observability logger usage."""
    # Create a temporary directory for logs
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Log directory: {tmpdir}")

        # Initialize the logger with custom configuration
        logger = get_observability_logger(
            logger_name="mlsdm_demo",
            log_dir=tmpdir,
            log_file="demo.log",
            max_bytes=5 * 1024 * 1024,  # 5 MB
            backup_count=3,
            max_age_days=7,
            console_output=True,  # Show logs in console
        )

        print("\n=== Demonstrating Logger Features ===\n")

        # 1. System startup event
        print("1. Logging system startup...")
        logger.log_system_startup(version="1.0.0", config={"dimension": 384, "capacity": 20000})

        # 2. Moral rejection event
        print("2. Logging moral rejection...")
        logger.log_moral_rejected(moral_value=0.3, threshold=0.5)

        # 3. Moral acceptance event
        print("3. Logging moral acceptance...")
        logger.log_moral_accepted(moral_value=0.8, threshold=0.5)

        # 4. Sleep phase transition
        print("4. Logging sleep phase transition...")
        logger.log_sleep_phase_entered(previous_phase="wake")

        # 5. Wake phase transition
        print("5. Logging wake phase transition...")
        time.sleep(0.1)  # Simulate some time passing
        logger.log_wake_phase_entered(previous_phase="sleep")

        # 6. Memory storage
        print("6. Logging memory store events...")
        for i in range(5):
            logger.log_memory_store(vector_dim=384, memory_size=100 + i)

        # 7. Memory full warning
        print("7. Logging memory full warning...")
        logger.log_memory_full(current_size=20000, capacity=20000, memory_mb=512.5)

        # 8. Processing time exceeded
        print("8. Logging processing time exceeded...")
        logger.log_processing_time_exceeded(processing_time_ms=1500.0, threshold_ms=1000.0)

        # 9. Generic events with custom metrics
        print("9. Logging generic events with custom metrics...")
        logger.info(
            EventType.EVENT_PROCESSED,
            "Processed input vector",
            metrics={
                "vector_dim": 384,
                "processing_time_ms": 25.5,
                "memory_usage_mb": 256.0,
            },
        )

        # 10. Error event with custom data
        print("10. Logging error event...")
        logger.error(
            EventType.SYSTEM_ERROR,
            "Failed to process request",
            metrics={"error_code": "E001", "retry_count": 3},
        )

        # 11. System shutdown
        print("11. Logging system shutdown...")
        logger.log_system_shutdown(reason="demo_complete")

        # Display logger configuration
        print("\n=== Logger Configuration ===")
        config = logger.get_config()
        for key, value in config.items():
            print(f"  {key}: {value}")

        # Show the log file contents
        print("\n=== Log File Contents (first 5 entries) ===")
        log_file = Path(tmpdir) / "demo.log"
        if log_file.exists():
            with open(log_file) as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:5], 1):
                    print(f"\nEntry {i}:")
                    # Pretty print JSON
                    import json

                    try:
                        log_entry = json.loads(line)
                        print(json.dumps(log_entry, indent=2))
                    except json.JSONDecodeError:
                        print(line)

            print(f"\n... and {len(lines) - 5} more entries")
            print(f"\nTotal log entries: {len(lines)}")
            print(f"Log file size: {log_file.stat().st_size} bytes")

        print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
