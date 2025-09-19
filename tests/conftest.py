"""Pytest configuration for test environment setup.

- Forces ``DISABLE_FILE_LOGS=1`` to avoid writing log files during tests.
- Ensures the project root is available on ``sys.path`` for imports.
"""

import os
import signal
import sys

os.environ.setdefault("DISABLE_FILE_LOGS", "1")  # Avoid creating log files during tests
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

_TEST_TIMEOUT = int(os.environ.get("PYTEST_TEST_TIMEOUT", "10"))


def _timeout_handler(signum, frame):
    """Test Timeout handler."""
    raise TimeoutError(f"Test exceeded {_TEST_TIMEOUT} seconds timeout")


def pytest_runtest_setup(item):
    """Test Pytest runtest setup."""
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(_TEST_TIMEOUT)
    except Exception:
        pass


def pytest_runtest_teardown(item, nextitem):
    """Test Pytest runtest teardown."""
    try:
        signal.alarm(0)
    except Exception:
        pass


# Make the `sys` module available as a builtin name for tests that
# reference it without an explicit import. Some older tests rely on
# the `sys` name being present in the global namespace.
try:
    import builtins

    builtins.sys = sys
except Exception:
    pass

# Provide a simple FakeLimiter in the builtin namespace so tests that
# reference `FakeLimiter` without importing it still work. Individual
# test modules may define their own more specific variants if needed.
try:

    class _SimpleFakeLimiter:
        """Test _SimpleFakeLimiter."""

        async def __aenter__(self):
            """Test Aenter."""
            return None

        async def __aexit__(self, *a, **k):
            """Test Aexit."""
            return False

    builtins.FakeLimiter = _SimpleFakeLimiter
except Exception:
    pass
