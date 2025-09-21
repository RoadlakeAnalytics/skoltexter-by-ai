"""Pipeline delegation helpers extracted from src.setup.app.

These thin wrappers forward calls into ``src.setup.pipeline.orchestrator``
while temporarily propagating prompt helpers from the main app module so
tests can reliably monkeypatch behaviour.
"""

from __future__ import annotations

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

        # Prefer explicit, concrete helpers so production code does not
        # depend on a legacy shim module in ``sys.modules``. Tests should
        # patch the concrete modules (for example ``src.setup.app_prompts``
        # or ``src.setup.app_runner``) rather than injecting a global
        # module object.
        try:
            from src.setup.app_prompts import ask_confirm as _ask_confirm, ask_text as _ask_text
        except Exception:
            _ask_confirm = getattr(orch, "ask_confirm", None)
            _ask_text = getattr(orch, "ask_text", None)

        try:
            from src.setup.app_runner import run_ai_connectivity_check_interactive as _run_check
        except Exception:
            _run_check = getattr(orch, "run_ai_connectivity_check_interactive", None)

        for _n, _f in (
            ("ask_confirm", _ask_confirm),
            ("ask_text", _ask_text),
            ("run_ai_connectivity_check_interactive", _run_check),
        ):
            if _f is not None:
                replaced[_n] = getattr(orch, _n, None)
                setattr(orch, _n, _f)
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

        # Use explicit concrete helpers instead of reading from a legacy
        # shim module. This makes behaviour predictable and easier for
        # tests to patch without relying on global module state.
        try:
            from src.setup.app_prompts import ask_confirm as _ask_confirm, ask_text as _ask_text
        except Exception:
            _ask_confirm = getattr(orch, "ask_confirm", None)
            _ask_text = getattr(orch, "ask_text", None)

        try:
            from src.setup.app_runner import run_ai_connectivity_check_interactive as _run_check
        except Exception:
            _run_check = getattr(orch, "run_ai_connectivity_check_interactive", None)

        for _n, _f in (
            ("ask_confirm", _ask_confirm),
            ("ask_text", _ask_text),
            ("run_ai_connectivity_check_interactive", _run_check),
        ):
            if _f is not None:
                replaced[_n] = getattr(orch, _n, None)
                setattr(orch, _n, _f)
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
