"""Load test configuration — add local directory to sys.path for async_utils imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
