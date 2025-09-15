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
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

import signal

_TEST_TIMEOUT = int(os.environ.get("PYTEST_TEST_TIMEOUT", "10"))


def _timeout_handler(signum, frame):
    raise TimeoutError(f"Test exceeded {_TEST_TIMEOUT} seconds timeout")


def pytest_runtest_setup(item):
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(_TEST_TIMEOUT)
    except Exception:
        pass


def pytest_runtest_teardown(item, nextitem):
    try:
        signal.alarm(0)
    except Exception:
        pass
