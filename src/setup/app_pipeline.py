"""Pipeline delegation helpers extracted from src.setup.app.

These thin wrappers forward calls into ``src.setup.pipeline.orchestrator``
while temporarily propagating prompt helpers from the main app module so
tests can reliably monkeypatch behaviour.
"""

from __future__ import annotations

import sys
from typing import Any


def _run_pipeline_step(*args: Any, **kwargs: Any) -> Any:
    from src.setup.pipeline.orchestrator import _run_pipeline_step as _impl

    return _impl(*args, **kwargs)


def _render_pipeline_table(*args: Any, **kwargs: Any) -> Any:
    from src.setup.pipeline.orchestrator import _render_pipeline_table as _impl

    return _impl(*args, **kwargs)


def _status_label(base: str) -> str:
    from src.setup.pipeline.orchestrator import _status_label as _impl

    return _impl(base)


def _run_processing_pipeline_plain() -> None:
    try:
        import importlib

        orch = importlib.import_module("src.setup.pipeline.orchestrator")
        replaced: dict[str, object | None] = {}
        app_mod = sys.modules.get("src.setup.app")
        for _n in ("ask_confirm", "ask_text", "run_ai_connectivity_check_interactive"):
            if hasattr(app_mod, _n):
                replaced[_n] = getattr(orch, _n, None)
                setattr(orch, _n, getattr(app_mod, _n))
    except Exception:
        orch = None
        replaced = {}

    try:
        from src.setup.pipeline.orchestrator import (
            _run_processing_pipeline_plain as _impl,
        )

        return _impl()
    finally:
        if orch is not None:
            for _n, _old in replaced.items():
                try:
                    if _old is None:
                        delattr(orch, _n)
                    else:
                        setattr(orch, _n, _old)
                except Exception:
                    pass


def _run_processing_pipeline_rich(*args: Any, **kwargs: Any) -> None:
    try:
        import importlib

        orch = importlib.import_module("src.setup.pipeline.orchestrator")
        replaced: dict[str, object | None] = {}
        app_mod = sys.modules.get("src.setup.app")
        for _n in ("ask_confirm", "ask_text", "run_ai_connectivity_check_interactive"):
            if hasattr(app_mod, _n):
                replaced[_n] = getattr(orch, _n, None)
                setattr(orch, _n, getattr(app_mod, _n))
    except Exception:
        orch = None
        replaced = {}

    try:
        from src.setup.pipeline.orchestrator import (
            _run_processing_pipeline_rich as _impl,
        )

        return _impl(*args, **kwargs)
    finally:
        if orch is not None:
            for _n, _old in replaced.items():
                try:
                    if _old is None:
                        delattr(orch, _n)
                    else:
                        setattr(orch, _n, _old)
                except Exception:
                    pass


__all__ = [
    "_run_pipeline_step",
    "_render_pipeline_table",
    "_status_label",
    "_run_processing_pipeline_plain",
    "_run_processing_pipeline_rich",
]

