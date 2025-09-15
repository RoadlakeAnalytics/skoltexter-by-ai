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

# When tests are executed under mutmut's working copy (./mutants), ensure the
# real project root is also importable so top-level modules like
# 'setup_project.py' can be imported by tests.
if ROOT.name == "mutants":
    REAL_ROOT = ROOT.parent
    real_root_str = str(REAL_ROOT)
    if real_root_str not in sys.path:
        sys.path.insert(0, real_root_str)
    # Ensure a top-level setup_project.py exists in the mutants workspace so
    # tests that import it via an absolute file path can succeed. We create a
    # tiny shim that re-exports symbols from the real project root.
    shim = ROOT / "setup_project.py"
    if not shim.exists():
        try:
            shim.write_text(
                (
                    "# Auto-generated shim for mutmut test environment\n"
                    "import sys, importlib.util as _il\nfrom pathlib import Path\n"
                    "REAL_ROOT = Path(__file__).resolve().parent.parent\n"
                    "p = str(REAL_ROOT)\n"
                    "(p not in sys.path) and sys.path.insert(0, p)\n"
                    "_path = REAL_ROOT / 'setup_project.py'\n"
                    "_spec = _il.spec_from_file_location('setup_project_norich_real', str(_path))\n"
                    "_mod = _il.module_from_spec(_spec)\n"
                    "assert _spec and _spec.loader\n"
                    "_spec.loader.exec_module(_mod)\n"
                    "globals().update({k: getattr(_mod, k) for k in dir(_mod) if not k.startswith('_')})\n"
                ),
                encoding="utf-8",
            )
        except Exception:
            # Best-effort; mutation run may still succeed due to PYTHONPATH in gate
            pass
