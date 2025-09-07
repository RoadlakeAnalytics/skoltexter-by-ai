"""Pytest configuration for test environment setup.

- Forces ``DISABLE_FILE_LOGS=1`` to avoid writing log files during tests.
- Ensures the project root is available on ``sys.path`` for imports.
"""

import os
import sys

os.environ.setdefault("DISABLE_FILE_LOGS", "1")  # Avoid creating log files during tests
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
