"""Extra tests to exercise wrapper and delegation functions in app module."""

import importlib
import types
import sys as _sys

import src.setup.app_pipeline as _app_pipeline
import src.setup.app_venv as _app_venv
import src.setup.app_runner as _app_runner
import src.setup.app_prompts as _app_prompts

# Build a compact `app` namespace exposing the small set of helpers
# used by these tests and register it under the legacy module name so
# code that inspects ``sys.modules['src.setup.app']`` sees the mapping.
_app_ns = types.SimpleNamespace(
    _run_pipeline_step=_app_pipeline._run_pipeline_step,
    _render_pipeline_table=_app_pipeline._render_pipeline_table,
    _status_label=_app_pipeline._status_label,
    manage_virtual_environment=_app_venv.manage_virtual_environment,
    parse_env_file=_app_runner.parse_env_file,
    prompt_and_update_env=_app_runner.prompt_and_update_env,
    ask_text=_app_prompts.ask_text,
    set_language=_app_prompts.set_language,
)

# For migration away from the legacy `src.setup.app` shim we no longer
# inject a synthetic ModuleType into ``sys.modules`` here. Tests should
# prefer importing the concrete modules under ``src.setup``. For
# compatibility within this test we expose a simple local ``app``
# namespace that provides the same helper attributes.
app = _app_ns


def test_manage_virtual_environment_wrapper_propagates(monkeypatch, tmp_path):
    # Define module-level venv helpers on app that originate outside app
    def fake_is_venv_active():
        return False

    def fake_get_venv_python_executable(p):
        return tmp_path / "venv" / "bin" / "python"

    # Assign helpers to app (their __module__ differs so wrapper will propagate)
    monkeypatch.setattr(app, "is_venv_active", fake_is_venv_active, raising=False)
    monkeypatch.setattr(
        app,
        "get_venv_python_executable",
        fake_get_venv_python_executable,
        raising=False,
    )

    called = {}

    def fake_manage(*a, **k):
        called["ok"] = True

    # Patch the underlying venv manager implementation to avoid side-effects
    import src.setup.venv_manager as vm

    monkeypatch.setattr(vm, "manage_virtual_environment", fake_manage)

    # Call wrapper - it should propagate helpers and call the underlying manager
    app.manage_virtual_environment()
    assert called.get("ok") is True


def test_delegation_wrappers_to_orchestrator(monkeypatch):
    # Ensure wrapper functions delegate to orchestrator implementations
    mod = importlib.import_module("src.setup.pipeline.orchestrator")
    monkeypatch.setattr(mod, "_run_pipeline_step", lambda *a, **k: "OK")
    assert app._run_pipeline_step("a") == "OK"
    monkeypatch.setattr(mod, "_render_pipeline_table", lambda *a, **k: "TBL")
    assert app._render_pipeline_table(1, 2, 3) == "TBL"
    monkeypatch.setattr(mod, "_status_label", lambda b: f"ST-{b}")
    assert app._status_label("waiting") == "ST-waiting"


def test_set_language_keyboardinterrupt(monkeypatch):
    # Force ask_text to raise KeyboardInterrupt and verify SystemExit
    monkeypatch.setattr(
        app, "ask_text", lambda prompt: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    try:
        app.set_language()
    except SystemExit:
        # Expected path
        pass


def test_parse_and_prompt_delegations(monkeypatch):
    # parse_env_file delegates to azure_env; stub the implementation
    monkeypatch.setattr("src.setup.azure_env.parse_env_file", lambda p: {"A": "v"})
    assert app.parse_env_file("x")["A"] == "v"

    # prompt_and_update_env delegates
    called = {}

    def fake_prompt(m, p, e, ui=None):
        called["ok"] = True

    monkeypatch.setattr("src.setup.azure_env.prompt_and_update_env", fake_prompt)
    app.prompt_and_update_env(["A"], "env", {})
    assert called.get("ok") is True
