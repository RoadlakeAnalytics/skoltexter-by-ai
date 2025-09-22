"""Delegated wrapper interface for pipeline orchestration and testable monkeypatching.

Short Summary
-------------
Provides high-clarity wrapper functions that delegate orchestration to
`src.setup.pipeline.orchestrator`, enabling robust CI integration, safe test monkeypatching,
and strict separation of pipeline boundaries. No business logic or orchestration state is
duplicated; these interfaces only delegate and temporarily inject helpers for reliable UI and test control.

Extended Summary
----------------
This module is intentionally minimal and portfolio-compliant: each wrapper exposes a single-responsibility delegation
to the orchestrator layer. They're extracted from the main app entrypoint for architectural purity, clean CI/test boundaries,
and precise injection of interactive helpers (`ask_confirm`, etc.) during runtime or tests. All helper patching is temporary
(state always reverted) to prevent leaks. Integration complexity (Rich UI, text UI, CLI) is handled only downstream.

Boundaries and System Context
-----------------------------
- Only orchestration delegation and prompt monkeypatching are permitted here. No pipeline logic or state.
- All business/data processing occurs in `src.setup.pipeline.orchestrator`.
- Helpers may be patched for UI/test—this is reverted after use.
- CI, pytest, and xdoctest may target these wrappers for injection or coverage testing.

Usage
-----
>>> from src.setup import app_pipeline
>>> result = app_pipeline._run_pipeline_step("step_name")
>>> print(result)
some_pipeline_step_result

References
----------
- AGENTS.md: School Data Pipeline Project Standards.
- src/setup/pipeline/orchestrator.py: All orchestration logic.
- src/setup/app_prompts.py, src/setup/app_runner.py: Interactive helpers.
- Portfolio docstring standard: NumPy + custom pipeline rules.

Examples
--------
>>> from src.setup import app_pipeline
>>> res = app_pipeline._status_label("running")
>>> print(res)
"[bold yellow]Running[/bold yellow]"
>>> table = app_pipeline._render_pipeline_table({"steps": [...]})
>>> print(table)
# (Rich Table object, or test-stable output)
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
    directly to the orchestrator implementation, enabling CI/test patching and UI flexibility.

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
        Any exception propagated from the orchestrator downstream (should be pipeline-specific).

    See Also
    --------
    src.setup.pipeline.orchestrator._render_pipeline_table

    Notes
    -----
    No custom logic is present here; pure delegation for coverage and separation.

    Examples
    --------
    >>> tbl = _render_pipeline_table({"step": "ai"})
    >>> assert "ai" in str(tbl)
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

        # Prefer explicit, concrete helpers so production code does not
        # depend on a legacy shim module in ``sys.modules``. Tests should
        # patch the concrete modules (for example ``src.setup.app_prompts``
        # or ``src.setup.app_runner``) rather than injecting a global
        # module object.
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

        # Use explicit concrete helpers instead of reading from a legacy
        # shim module. This makes behaviour predictable and easier for
        # tests to patch without relying on global module state.
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
