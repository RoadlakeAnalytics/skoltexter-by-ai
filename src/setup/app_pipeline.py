"""Thin wrappers that delegate orchestration operations to the orchestrator.

This module provides minimal wrapper functions that forward calls to the
implementations in ``src.setup.pipeline.orchestrator``. The wrappers exist to
expose a stable import surface for setup code and to simplify testing.

Examples
--------
>>> from src.setup import app_pipeline
>>> result = app_pipeline._run_pipeline_step("step_name")
>>> print(result)
"""

from __future__ import annotations

from typing import Any, Optional
from typing import Callable


def _run_pipeline_step(*args: Any, **kwargs: Any) -> Any:
    r"""Delegate a pipeline step execution to the orchestrator.

    Passes all provided arguments to the downstream `_run_pipeline_step`
    implementation from `src.setup.pipeline.orchestrator`. This is a thin
    wrapper used for testability and dependency decoupling.

    Parameters
    ----------
    *args : Any
        Positional arguments forwarded to the orchestrator.
    **kwargs : Any
        Keyword arguments forwarded to the orchestrator.

    Returns
    -------
    Any
        The result of the delegated pipeline step, as produced by the orchestrator.

    Raises
    ------
    Exception
        Any exception raised downstream by the orchestrator.

    See Also
    --------
    src.setup.pipeline.orchestrator._run_pipeline_step

    Notes
    -----
    No business logic is performed here. Used for isolation and monkeypatching in tests.

    Examples
    --------
    >>> out = _run_pipeline_step("data_ingest")
    >>> print(out)
    {'status': 'success', 'details': ...}
    """
    from src.setup.pipeline.orchestrator import _run_pipeline_step as _impl

    return _impl(*args, **kwargs)


def _render_pipeline_table(*args: Any, **kwargs: Any) -> Any:
    r"""Render pipeline status and metadata table via orchestration delegate.

    Summarizes the pipeline state or recent steps using the orchestrator's Rich table
    renderer or other output format, depending on configuration. All arguments are passed
    directly to the orchestrator implementation.

    Parameters
    ----------
    *args : Any
        Positional arguments forwarded to the orchestrator's table renderer.
    **kwargs : Any
        Keyword arguments forwarded to the orchestrator's table renderer.

    Returns
    -------
    Any
        Pipeline table object, rich output, or test-stable summary as produced by the orchestrator.

    Raises
    ------
    Exception
        Any exception propagated from the orchestrator downstream.

    See Also
    --------
    src.setup.pipeline.orchestrator._render_pipeline_table

    Notes
    -----
    This is a pure delegation helper; callers should consult the orchestrator
    implementation for rendering details.
    """
    from src.setup.pipeline.orchestrator import _render_pipeline_table as _impl

    return _impl(*args, **kwargs)


def _status_label(base: str) -> str:
    from src.setup.pipeline.orchestrator import _status_label as _impl

    return _impl(base)


def _run_processing_pipeline_plain() -> None:
    orch = None
    replaced: dict[str, Any | None] = {}
    _ask_confirm: Optional[Callable[[str, bool], bool]] = None
    _ask_text: Optional[Callable[[str, Optional[str]], str]] = None
    _run_check: Optional[Callable[[], bool]] = None
    try:
        import importlib

        orch = importlib.import_module("src.setup.pipeline.orchestrator")

        try:
            from src.setup.app_prompts import (
                ask_confirm as _ask_confirm,
                ask_text as _ask_text,
            )
        except Exception:
            _ask_confirm = getattr(orch, "ask_confirm", None)
            _ask_text = getattr(orch, "ask_text", None)

        try:
            from src.setup.app_runner import (
                run_ai_connectivity_check_interactive as _run_check,
            )
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
    orch = None
    replaced: dict[str, Any | None] = {}
    _ask_confirm: Optional[Callable[[str, bool], bool]] = None
    _ask_text: Optional[Callable[[str, Optional[str]], str]] = None
    _run_check: Optional[Callable[[], bool]] = None
    try:
        import importlib

        orch = importlib.import_module("src.setup.pipeline.orchestrator")

        try:
            from src.setup.app_prompts import (
                ask_confirm as _ask_confirm,
                ask_text as _ask_text,
            )
        except Exception:
            _ask_confirm = getattr(orch, "ask_confirm", None)
            _ask_text = getattr(orch, "ask_text", None)

        try:
            from src.setup.app_runner import (
                run_ai_connectivity_check_interactive as _run_check,
            )
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

