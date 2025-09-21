"""Canonical tests for the ``src.setup.app_pipeline`` wrappers.

These tests verify that the thin delegation wrappers in
``src.setup.app_pipeline`` correctly forward calls to the concrete
implementations in ``src.setup.pipeline.orchestrator`` and that the
pipeline entrypoints behave as expected when the underlying helpers are
patched. Tests patch concrete modules (not the legacy shim) so they are
isolated and deterministic.
"""

from __future__ import annotations

from typing import Any
import importlib

import src.setup.app_pipeline as app_pipeline


def test_delegation_wrappers_to_orchestrator(monkeypatch):
    """Ensure wrapper functions delegate to orchestrator implementations.

    The wrapper functions in :mod:`src.setup.app_pipeline` are thin
    adapters that import the real implementation from
    :mod:`src.setup.pipeline.orchestrator` at call time. This test
    patches the concrete orchestrator module to ensure delegation is
    performed correctly.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to install temporary attributes on the orchestrator.

    Returns
    -------
    None
    """
    mod = importlib.import_module("src.setup.pipeline.orchestrator")
    monkeypatch.setattr(mod, "_run_pipeline_step", lambda *a, **k: "OK")
    assert app_pipeline._run_pipeline_step("a") == "OK"
    monkeypatch.setattr(mod, "_render_pipeline_table", lambda *a, **k: "TBL")
    assert app_pipeline._render_pipeline_table(1, 2, 3) == "TBL"
    monkeypatch.setattr(mod, "_status_label", lambda b: f"ST-{b}")
    assert app_pipeline._status_label("waiting") == "ST-waiting"


def test_run_processing_pipeline_wrappers_delegate(monkeypatch):
    """Wrappers around orchestrator's pipeline entrypoints should delegate.

    The in-process wrappers call into the orchestrator module; patch the
    orchestrator implementations and assert the wrappers return the
    patched values.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to apply temporary patches.

    Returns
    -------
    None
    """
    orch = importlib.import_module("src.setup.pipeline.orchestrator")
    monkeypatch.setattr(orch, "_run_processing_pipeline_plain", lambda: "PLAIN_OK")
    monkeypatch.setattr(orch, "_run_processing_pipeline_rich", lambda *a, **k: "RICH_OK")
    assert app_pipeline._run_processing_pipeline_plain() == "PLAIN_OK"
    assert app_pipeline._run_processing_pipeline_rich() == "RICH_OK"


def test_run_processing_pipeline_rich(monkeypatch):
    """Exercise the rich-processing pipeline runner with patched helpers.

    The test patches concrete dependencies (including the Azure connectivity
    check) so no network calls or global shim mutation occurs.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to install fakes.

    Returns
    -------
    None
    """
    updates: list[Any] = []

    def updater(x: Any) -> None:
        updates.append(x)

    # Patch concrete helpers to avoid interactive prompts and network calls.
    monkeypatch.setattr("src.setup.pipeline.orchestrator.ask_confirm", lambda *a, **k: True)
    monkeypatch.setattr("src.setup.azure_env.run_ai_connectivity_check_silent", lambda: (True, "ok"))
    monkeypatch.setattr("src.setup.pipeline.orchestrator._run_pipeline_step", lambda *a, **k: True)
    monkeypatch.setattr(
        "src.setup.pipeline.orchestrator._render_pipeline_table",
        lambda s1, s2, s3: f"T:{s1},{s2},{s3}",
    )
    monkeypatch.setattr("src.setup.pipeline.orchestrator._status_label", lambda b: b)

    app_pipeline._run_processing_pipeline_rich(content_updater=updater)
    assert len(updates) >= 2


def test_run_processing_pipeline_plain_early(monkeypatch):
    """Exercise the plain-processing pipeline runner when user aborts early.

    Patches orchestrator prompt and pipeline step helpers to avoid
    interactive prompts and heavy processing.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch orchestrator helpers.

    Returns
    -------
    None
    """
    # Patch the concrete prompt helper used by the wrapper so the
    # behaviour is deterministic even when the wrapper temporarily
    # installs concrete helpers onto the orchestrator module.
    monkeypatch.setattr("src.setup.app_prompts.ask_confirm", lambda *a, **k: False)
    monkeypatch.setattr("src.setup.pipeline.orchestrator._run_pipeline_step", lambda *a, **k: False)
    app_pipeline._run_processing_pipeline_plain()
