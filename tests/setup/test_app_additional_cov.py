"""Additional tests exercising branches in the concrete setup modules.

These tests were migrated away from the legacy `src.setup.app` shim and
now patch the concrete modules used by the application. This avoids
global mutable shims in `sys.modules` and makes test dependencies
explicit.
"""

from types import SimpleNamespace
import importlib
import types

import src.setup.app_ui as _app_ui
