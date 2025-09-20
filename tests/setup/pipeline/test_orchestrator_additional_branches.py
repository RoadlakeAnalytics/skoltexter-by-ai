"""Targeted tests for ``src.setup.pipeline.orchestrator`` branches.

These tests exercise the TUI composition helper, the set/restore
behaviour for TUI mode, the AI connectivity interactive reporting, and
the decision logic in ``_run_pipeline_step``.

"""

from types import SimpleNamespace

import src.setup.pipeline.orchestrator as orch


def test_compose_and_update_group_and_single(monkeypatch) -> None:
    """_compose_and_update calls the registered updater with composed content.

    When both ``_STATUS_RENDERABLE`` and ``_PROGRESS_RENDERABLE`` are set
    and TUI mode is enabled, the updater should be invoked with a
    container exposing an ``items`` attribute holding the two renderables.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to set module globals safely.

    Returns
    -------
    None
    """
    recorded = []

    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda obj: recorded.append(obj), raising=False)
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", "S", raising=False)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", "P", raising=False)

    orch._compose_and_update()
    assert recorded, "Updater should have been called"
    content = recorded[0]
    # The composed content should expose .items with the two elements
    assert hasattr(content, "items") and tuple(content.items) == ("S", "P")


def test_set_tui_mode_and_restore(monkeypatch) -> None:
    """set_tui_mode returns a restore callable that reinstates previous state.

    The test sets the TUI mode to a known value, calls ``set_tui_mode`` and
    then invokes the returned restore to ensure previous globals are
    restored.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to isolate module globals.

    Returns
    -------
    None
    """
    # Record previous state and apply a new mode
    prev = (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER)
    restore = orch.set_tui_mode(lambda v: None, lambda p: None)
    assert orch._TUI_MODE is True
    # Restore and verify previous state is reinstated
    restore()
    assert (orch._TUI_MODE, orch._TUI_UPDATER, orch._TUI_PROMPT_UPDATER) == prev


def test_run_ai_connectivity_check_interactive(monkeypatch) -> None:
    """Interactive connectivity reporting prints success or failure.

    Monkeypatch the silent connectivity checker to return both success
    and failure scenarios and ensure the function returns the expected
    boolean and emits text via ``rprint``.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to stub the silent connectivity checker and rprint.

    Returns
    -------
    None
    """
    printed = []
    monkeypatch.setattr(orch, "rprint", lambda *a, **k: printed.append(a[0] if a else ""), raising=False)

    # Success case
    monkeypatch.setattr(orch, "run_ai_connectivity_check_silent", lambda: (True, "ok"), raising=False)
    assert orch.run_ai_connectivity_check_interactive() is True
    assert printed, "Should have printed a success message"

    printed.clear()
    # Failure case
    monkeypatch.setattr(orch, "run_ai_connectivity_check_silent", lambda: (False, "bad"), raising=False)
    assert orch.run_ai_connectivity_check_interactive() is False
    assert printed, "Should have printed failure details"


def test__run_pipeline_step_variants(monkeypatch) -> None:
    """Exercise success, failure, skip and invalid branches of _run_pipeline_step.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to stub UI prompts and program execution.

    Returns
    -------
    None
    """
    calls = {}

    # Helper stubs for UI notifications
    monkeypatch.setattr(orch, "ui_success", lambda msg: calls.setdefault("success", []).append(msg), raising=False)
    monkeypatch.setattr(orch, "ui_warning", lambda msg: calls.setdefault("warning", []).append(msg), raising=False)
    monkeypatch.setattr(orch, "ui_info", lambda msg: calls.setdefault("info", []).append(msg), raising=False)

    # Success path: ask 'y' and run_program returns True
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "y", raising=False)
    monkeypatch.setattr(orch, "run_program", lambda name, path, stream_output=False: True, raising=False)
    ok = orch._run_pipeline_step("run_program_1_prompt", "program_1", None, "program_1_failed", "program_1_complete")
    assert ok is True and "success" in calls

    calls.clear()
    # Failure path: ask 'y' and run_program returns False
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "y", raising=False)
    monkeypatch.setattr(orch, "run_program", lambda name, path, stream_output=False: False, raising=False)
    ok2 = orch._run_pipeline_step("run_program_1_prompt", "program_1", None, "program_1_failed", "program_1_complete")
    assert ok2 is False and "warning" in calls

    calls.clear()
    # Skip path: ask 's' and skip_message provided
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "s", raising=False)
    ok3 = orch._run_pipeline_step(
        "run_program_2_prompt",
        "program_2",
        None,
        "program_2_failed",
        "program_2_complete",
        skip_message="program_2_skipped",
    )
    assert ok3 is True or ok3 is None or "info" in calls

    calls.clear()
    # Invalid choice: other input
    monkeypatch.setattr(orch, "ask_text", lambda prompt, default="y": "x", raising=False)
    ok4 = orch._run_pipeline_step("run_program_3_prompt", "program_3", None, "program_3_failed", "program_3_complete")
    assert ok4 is False and "warning" in calls


def test_compose_and_update_other_branches(monkeypatch) -> None:
    """Cover single-renderable and empty-renderable composition paths.

    This exercises branches where only status or only progress is
    present, and the fallback where neither is present resulting in an
    empty Panel being emitted to the updater.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to set module globals safely.

    Returns
    -------
    None
    """
    recorded = []
    # Only status
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda obj: recorded.append(("only_status", obj)), raising=False)
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", "SINGLE", raising=False)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", None, raising=False)
    orch._compose_and_update()
    assert recorded and recorded[-1][0] == "only_status"

    # Only progress
    recorded.clear()
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", "PROG", raising=False)
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", None, raising=False)
    orch._compose_and_update()
    assert recorded and recorded[-1][0] == "only_status"

    # Neither present -> fallback Panel
    recorded.clear()
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", None, raising=False)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", None, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda obj: recorded.append(("empty", obj)), raising=False)
    orch._compose_and_update()
    assert recorded and recorded[0][0] == "empty"


def test_compose_and_update_group_setattr_failure(monkeypatch) -> None:
    """Simulate a Group type whose instance cannot have attributes set.

    The orchestrator should ignore failures while attempting to add an
    ``items`` attribute to the rich Group object and still call the
    updater with the Group instance.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for temporary patching of the console_helpers Group class.

    Returns
    -------
    None
    """
    class BadGroup:
        def __init__(self, a, b):
            # store but disallow adding new attributes afterwards
            object.__setattr__(self, "a", a)
            object.__setattr__(self, "b", b)

        def __setattr__(self, name, value):
            # refuse setting any attribute to trigger the exception path
            raise AttributeError("cannot set")

    # Patch the console_helpers Group used inside orchestrator
    import importlib, src.setup.console_helpers as ch

    monkeypatch.setattr(ch, "Group", BadGroup, raising=False)

    recorded = []
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda obj: recorded.append(obj), raising=False)
    monkeypatch.setattr(orch, "_STATUS_RENDERABLE", "S", raising=False)
    monkeypatch.setattr(orch, "_PROGRESS_RENDERABLE", "P", raising=False)
    orch._compose_and_update()
    assert recorded, "Updater should have been called even when Group setattr fails"
