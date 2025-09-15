"""Tests for setup_project: interactive CLI, venv, pipeline, logs, and i18n.

Covers language selection, questionary fallbacks, venv creation/recreation and
install flows, subprocess runners, menu handling, log viewing, environment
helpers, Azure .env prompting, resets, and various error branches.
"""

import sys
from pathlib import Path

import pytest

import setup_project as sp

# ---- Extra paths consolidated from test_setup_entry.py ----


def test_entry_point_basic(monkeypatch):
    # Run entry_point with --lang en and --no-venv to cover the flow
    monkeypatch.setattr(sys, "argv", ["setup_project.py", "--lang", "en", "--no-venv"])
    # Avoid interactive pauses
    monkeypatch.setattr(sp, "set_language", lambda: None)
    monkeypatch.setattr(sp, "main_menu", lambda: None)
    monkeypatch.setattr(sp, "ensure_azure_openai_env", lambda: None)
    # Avoid exiting pytest
    monkeypatch.setattr(sp.sys, "exit", lambda code=0: None)
    sp.entry_point()


# ---- Extra paths consolidated from test_setup_menu.py ----


def test_main_menu_choices_consolidated(monkeypatch):
    calls = {"env": 0, "desc": 0, "pipe": 0, "logs": 0, "reset": 0}
    monkeypatch.setattr(
        sp,
        "manage_virtual_environment",
        lambda: calls.__setitem__("env", calls["env"] + 1),
    )
    monkeypatch.setattr(
        sp,
        "view_program_descriptions",
        lambda: calls.__setitem__("desc", calls["desc"] + 1),
    )
    monkeypatch.setattr(
        sp,
        "run_processing_pipeline",
        lambda: calls.__setitem__("pipe", calls["pipe"] + 1),
    )
    monkeypatch.setattr(
        sp, "view_logs", lambda: calls.__setitem__("logs", calls["logs"] + 1)
    )
    monkeypatch.setattr(
        sp, "reset_project", lambda: calls.__setitem__("reset", calls["reset"] + 1)
    )
    seq = iter(["1", "2", "3", "4", "5", "6"])  # exercise each menu path then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.main_menu()
    assert calls == {"env": 1, "desc": 1, "pipe": 1, "logs": 1, "reset": 1}


def test_set_language_invalid_then_ok_consolidated(monkeypatch):
    prev = sp.LANG
    seq = iter(["x", "1"])  # invalid then English
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    try:
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


# ---- Extra paths consolidated from test_setup_extra_paths.py ----


def test_questionary_paths(monkeypatch):
    class Q:
        @staticmethod
        def text(prompt, default=""):
            class A:
                def ask(self):
                    return "value"

            return A()

        @staticmethod
        def confirm(prompt, default=True):
            class A:
                def ask(self):
                    return True

            return A()

        @staticmethod
        def select(prompt, choices):
            class A:
                def ask(self):
                    return choices[-1]

            return A()

    monkeypatch.setattr(sp, "_HAS_Q", True)
    monkeypatch.setattr(sp, "questionary", Q)
    assert sp.ask_text("?") == "value"
    assert sp.ask_confirm("?") is True
    assert sp.ask_select("?", ["a", "b"]) == "b"


def test_get_venv_exec_on_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp.sys, "platform", "win32")
    v = tmp_path / "venv"
    assert sp.get_venv_bin_dir(v).name == "Scripts"
    assert sp.get_venv_python_executable(v).name == "python.exe"
    assert sp.get_venv_pip_executable(v).name == "pip.exe"


def test_translate_alias_unsupported_language(monkeypatch):
    prev = sp.LANG
    try:
        monkeypatch.setattr(sp, "LANG", "xx")
        # Should fall back to English without crashing
        assert isinstance(sp.translate("welcome"), str)
        assert isinstance(sp._("welcome"), str)
    finally:
        sp.LANG = prev


def test_set_language_exception_then_ok(monkeypatch):
    def raise_once(prompt):
        # First call raises, second returns '1'
        if getattr(raise_once, "_done", False):
            return "1"
        raise_once._done = True
        raise RuntimeError("boom")

    prev = sp.LANG
    try:
        monkeypatch.setattr(sp, "ask_text", raise_once)
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_get_python_executable_variants(monkeypatch, tmp_path: Path):
    # Active venv branch
    monkeypatch.setattr(sp, "is_venv_active", lambda: True)
    assert sp.get_python_executable() == sys.executable
    # Venv exists branch
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    fake_py = (
        tmp_path
        / "venv"
        / ("bin" if sys.platform != "win32" else "Scripts")
        / ("python.exe" if sys.platform == "win32" else "python")
    )
    fake_py.parent.mkdir(parents=True, exist_ok=True)
    fake_py.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")
    assert Path(sp.get_python_executable()).exists()


def test_manage_virtual_environment_remove_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")
    sp.VENV_DIR.mkdir()
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    seq = iter(["y", "y"])  # yes to manage, yes to recreate
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": next(seq))
    monkeypatch.setattr(
        sp.shutil, "rmtree", lambda p: (_ for _ in ()).throw(RuntimeError("rmtree"))
    )
    sp.manage_virtual_environment()  # should handle error and return


def test_manage_virtual_environment_create_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv2")
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    seq = iter(["y"])  # yes to create
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": next(seq))
    monkeypatch.setattr(
        sp.venv, "create", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("create"))
    )
    sp.manage_virtual_environment()


def test_manage_virtual_environment_install_errors(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "v3")
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "y")

    def fake_create(*a, **k):
        # Create fake bin/python to let code pick python
        bindir = tmp_path / "v3" / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(sp.venv, "create", fake_create)
    import subprocess as _sub

    # First, CalledProcessError
    calls = {"n": 0}

    def raise_cpe(args):
        calls["n"] += 1
        raise _sub.CalledProcessError(1, args)

    monkeypatch.setattr(sp.subprocess, "check_call", raise_cpe)
    sp.manage_virtual_environment()


def test_rich_ui_helpers_basic():
    """Exercise Rich UI helpers; ensure no exceptions during rendering."""
    import setup_project as sp_local

    sp_local.ui_rule("Test Section")
    sp_local.ui_header("Test Header")
    with sp_local.ui_status("Working..."):
        pass
    sp_local.ui_info("info")
    sp_local.ui_success("ok")
    sp_local.ui_warning("warn")
    sp_local.ui_error("err")
    sp_local.ui_menu([("1", "Alpha"), ("2", "Beta")])


def test_manage_virtual_environment_dynamic_ui_enable_success(monkeypatch):
    """Run venv management with active venv to hit dynamic UI-enable branch."""
    import setup_project as sp_local

    monkeypatch.setattr(sp_local, "is_venv_active", lambda: True)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()


def test_rich_import_fallback_module_load(monkeypatch, tmp_path: Path):
    """Re-import setup_project with Rich import failing to cover fallback path."""
    import builtins
    import importlib.util

    orig_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("no rich for this test")
        return orig_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    spec = importlib.util.spec_from_file_location(
        "setup_project_norich",
        str(Path(__file__).resolve().parents[1] / "setup_project.py"),
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader  # for mypy
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    assert hasattr(mod, "ui_has_rich") and mod.ui_has_rich() is False
    mod.ui_rule("Fallback Rule")
    mod.ui_header("Fallback Header")
    with mod.ui_status("Working..."):
        pass
    mod.ui_info("info")
    mod.ui_success("ok")
    mod.ui_warning("warn")
    mod.ui_error("err")
    mod.ui_menu([("1", "Alpha"), ("2", "Beta")])


def test_ai_connectivity_unexpected_reply(monkeypatch):
    """Cover the unexpected reply branch (HTTP 200 with non-OK content)."""
    import sys as _sys
    import types

    import setup_project as sp_local

    class FakeCfg:
        def __init__(self):
            self.gpt4o_endpoint = "https://x"
            self.api_key = "k"
            self.request_timeout = 1

    class FakeResp:
        status = 200

        async def text(self):
            return '{"choices": [{"message": {"content": "Not OK"}}]}'

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSess:
        def __init__(self, *a, **k):
            pass

        def post(self, *a, **k):
            return FakeResp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_mod = types.SimpleNamespace(OpenAIConfig=FakeCfg)
    monkeypatch.setitem(_sys.modules, "src.program2_ai_processor", fake_mod)
    fake_aiohttp = types.SimpleNamespace(
        ClientSession=FakeSess, ClientTimeout=lambda total=None: None
    )
    monkeypatch.setitem(_sys.modules, "aiohttp", fake_aiohttp)

    assert sp_local.run_ai_connectivity_check_interactive() is False


def test_manage_virtual_environment_dynamic_ui_enable_excepts(monkeypatch):
    """Drive except branches inside dynamic UI-enablement (rich/questionary failures)."""
    import builtins as _builtins
    import importlib as _importlib

    import setup_project as sp_local

    monkeypatch.setattr(sp_local, "is_venv_active", lambda: True)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    # Avoid rich.print usage within the function to prevent import side effects
    monkeypatch.setattr(sp_local, "rprint", lambda *a, **k: None)
    monkeypatch.setattr(sp_local, "ui_has_rich", lambda: False)

    orig_import = _builtins.__import__

    def fake_import(name, *a, **k):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("no rich now")
        return orig_import(name, *a, **k)

    monkeypatch.setattr(_builtins, "__import__", fake_import)
    monkeypatch.setattr(
        _importlib,
        "import_module",
        lambda module: (_ for _ in ()).throw(ImportError("no q")),
    )

    sp_local.manage_virtual_environment()

    # Then, FileNotFoundError
    def raise_fnf(args):
        raise FileNotFoundError("pip not found")

    monkeypatch.setattr(sp.subprocess, "check_call", raise_fnf)
    sp.manage_virtual_environment()


def test_run_program_stream_fail_and_exception(monkeypatch, tmp_path: Path):
    class P:
        def wait(self):
            return 1

    monkeypatch.setattr(sp, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp.subprocess, "Popen", lambda *a, **k: P())
    assert sp.run_program("program_1", tmp_path / "x.py", stream_output=True) is False

    monkeypatch.setattr(
        sp.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert sp.run_program("program_2", tmp_path / "x.py", stream_output=False) is False


def test_view_program_descriptions_invalid(monkeypatch):
    seq = iter(["invalid", "0"])  # invalid then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.view_program_descriptions()


def test_run_processing_pipeline_abort(monkeypatch):
    monkeypatch.setattr(sp, "ask_confirm", lambda *a, **k: False)
    monkeypatch.setattr(sp, "_run_pipeline_step", lambda *a, **k: False)
    sp.run_processing_pipeline()


def test_run_pipeline_step_skip_without_skip_message(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "skip")
    assert (
        sp._run_pipeline_step(
            "k", "program_2", tmp_path, "fail", "ok", skip_message=None
        )
        is True
    )


def test_view_logs_dir_exists_but_no_log_files(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    (tmp_path / "note.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "0")
    sp.view_logs()


def test_reset_project_cancel(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path / "logs")
    f = tmp_path / "data" / "output" / "x.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="n": "n")
    sp.reset_project()


def test_reset_project_rmdir_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path / "logs")
    base = tmp_path / "data" / "generated_markdown_from_csv"
    nested = base / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "f.txt").write_text("1", encoding="utf-8")
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="n": "y")

    orig_rmdir = Path.rmdir

    def flaky_rmdir(self):
        if self == nested:
            raise OSError("blocked")
        return orig_rmdir(self)

    monkeypatch.setattr(Path, "rmdir", flaky_rmdir)
    sp.reset_project()


def test_parse_env_file_not_exists(tmp_path: Path):
    assert sp.parse_env_file(tmp_path / "missing.env") == {}


def test_ensure_azure_openai_env_triggers_prompt(monkeypatch, tmp_path: Path):
    envp = tmp_path / ".env"
    envp.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "ENV_PATH", envp)
    called = {"n": 0}

    def fake_prompt(keys, env_path, existing):
        called["n"] += 1
        for k in keys:
            existing[k] = "x"

    monkeypatch.setattr(sp, "prompt_and_update_env", fake_prompt)
    sp.ensure_azure_openai_env()
    assert called["n"] == 1


def test_prompt_and_update_env_writes(monkeypatch, tmp_path: Path):
    envp = tmp_path / ".env"
    existing = {"EXTRA": "keep"}
    missing = list(sp.REQUIRED_AZURE_KEYS)
    seq_vals = iter(["k1", "k2", "k3", "k4"])  # for required keys
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq_vals))
    sp.prompt_and_update_env(missing, envp, existing)
    text = envp.read_text(encoding="utf-8")
    for k in sp.REQUIRED_AZURE_KEYS:
        assert k in text
    assert 'EXTRA="keep"' in text


# -- basic i18n and helpers --
def test_translate_and_alias_switch_language(monkeypatch):
    """Switch between languages and validate key translations.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        Fixture used to modify global language during the test.

    Returns
    -------
    None
    """
    assert sp.translate("welcome").startswith("Welcome")
    monkeypatch.setattr(sp, "LANG", "sv")
    assert sp.translate("welcome").startswith("Välkommen")
    assert sp._("exiting").lower().count("avslutar") > 0


def test_ask_text_confirm_and_select(monkeypatch):
    """Exercise input helpers via fallback paths.

    Parameters
    ----------
    monkeypatch : MonkeyPatch
        Fixture used to inject fake input values.

    Returns
    -------
    None
    """
    monkeypatch.setattr(sp, "_HAS_Q", False)
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "hello")
    assert sp.ask_text("Your name: ") == "hello"
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "")
    assert sp.ask_confirm("Continue?") is True
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "n")
    assert sp.ask_confirm("Continue?") is False
    monkeypatch.setattr(sys.modules["builtins"], "input", lambda _="": "2")
    assert sp.ask_select("Pick one", ["A", "B", "C"]) == "B"


def test_parse_env_and_find_missing(tmp_path: Path):
    """Parse a simple .env and check detection of missing keys."""
    env_path = tmp_path / ".env"
    env_path.write_text(
        'AZURE_API_KEY="abc"\nAZURE_ENDPOINT_BASE="https://x"\n', encoding="utf-8"
    )
    data = sp.parse_env_file(env_path)
    assert data["AZURE_API_KEY"] == "abc"
    missing = sp.find_missing_env_keys(data, sp.REQUIRED_AZURE_KEYS)
    assert "GPT4O_DEPLOYMENT_NAME" in missing and "AZURE_API_VERSION" in missing


# -- main units --
def test_set_language_switch(monkeypatch):
    """Drive set_language through Swedish then back to English."""
    prev = sp.LANG
    try:
        monkeypatch.setattr(sp, "ask_text", lambda prompt: "2")
        sp.set_language()
        assert sp.LANG == "sv"
        monkeypatch.setattr(sp, "ask_text", lambda prompt: "1")
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_prompt_virtual_environment_choice(monkeypatch):
    """Verify menu choice (1/2) maps to boolean as expected."""
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "1")
    assert sp.prompt_virtual_environment_choice() is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "2")
    assert sp.prompt_virtual_environment_choice() is False


def test_run_pipeline_step_variants(monkeypatch, tmp_path: Path):
    """Cover success, skip, and failure branches for a pipeline step."""
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp, "run_program", lambda *a, **k: True)
    ok = sp._run_pipeline_step("k1", "program_1", tmp_path, "fail", "ok")
    assert ok is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "s")
    ok2 = sp._run_pipeline_step("k1", "program_1", tmp_path, "fail", "ok")
    assert ok2 is True
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp, "run_program", lambda *a, **k: False)
    ok3 = sp._run_pipeline_step("k1", "program_1", tmp_path, "fail", "ok")
    assert ok3 is False


def test_run_processing_pipeline_ai_check(monkeypatch, tmp_path: Path):
    """Cover AI-check success and failure in pipeline runner."""
    calls = {"steps": 0}
    monkeypatch.setattr(sp, "ask_confirm", lambda prompt, default_yes=True: True)
    monkeypatch.setattr(
        sp,
        "_run_pipeline_step",
        lambda *a, **k: calls.__setitem__("steps", calls["steps"] + 1) or True,
    )
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: True)
    sp.run_processing_pipeline()
    assert calls["steps"] >= 2
    calls["steps"] = 0
    monkeypatch.setattr(sp, "run_ai_connectivity_check_interactive", lambda: False)
    sp.run_processing_pipeline()
    assert calls["steps"] == 0


def test_view_logs_no_logs(monkeypatch, tmp_path: Path):
    """View logs with an empty directory; ensures no crashes."""
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    monkeypatch.setattr(sp, "ask_text", lambda prompt: "0")
    sp.view_logs()


def test_reset_project_deletes(monkeypatch, tmp_path: Path):
    """Reset removes all generated files beneath project paths."""
    monkeypatch.setattr(sp, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path / "logs")
    paths = [
        tmp_path / "data/generated_markdown_from_csv/a.md",
        tmp_path / "data/ai_processed_markdown/b.md",
        tmp_path / "data/ai_raw_responses/c.json",
        tmp_path / "data/generated_descriptions/d.md",
        tmp_path / "output/index.html",
        tmp_path / "logs/x.log",
    ]
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="n": "y")
    sp.reset_project()
    assert not any(p.exists() for p in paths)


def test_run_program_stream_and_capture(monkeypatch, tmp_path: Path):
    """Exercise both stream and capture flows in run_program."""

    class P:
        def __init__(self, code):
            self._code = code

        def wait(self):
            return self._code

    def fake_popen(args, **kwargs):
        return P(0)

    monkeypatch.setattr(sp, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp.subprocess, "Popen", fake_popen)
    ok = sp.run_program("program_1", tmp_path / "f.py", stream_output=True)
    assert ok is True

    class R:
        def __init__(self, code):
            self.returncode = code
            self.stdout = "OUT"
            self.stderr = "ERR"

    monkeypatch.setattr(sp.subprocess, "run", lambda *a, **k: R(0))
    ok2 = sp.run_program("program_2", tmp_path / "f.py", stream_output=False)
    assert ok2 is True
    monkeypatch.setattr(sp.subprocess, "run", lambda *a, **k: R(2))
    ok3 = sp.run_program("program_2", tmp_path / "f.py", stream_output=False)
    assert ok3 is False


# ----- manage env flows -----
def _make_fake_bin(tmp: Path):
    bindir = tmp / ("Scripts" if sys.platform == "win32" else "bin")
    bindir.mkdir(parents=True, exist_ok=True)
    (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
        "", encoding="utf-8"
    )
    (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
        "", encoding="utf-8"
    )
    return bindir


def test_manage_virtual_environment_create(monkeypatch, tmp_path: Path):
    """Create venv flow: creates structure and installs deps (mocked)."""
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    seq = iter(["y"])  # yes to create
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": next(seq))
    called = {"create": False, "pip": []}

    def fake_create(*a, **k):
        called["create"] = True
        _make_fake_bin(sp.VENV_DIR)

    monkeypatch.setattr(sp.venv, "create", fake_create)
    monkeypatch.setattr(
        sp,
        "get_venv_python_executable",
        lambda v: (
            sp.VENV_DIR
            / ("Scripts" if sys.platform == "win32" else "bin")
            / ("python.exe" if sys.platform == "win32" else "python")
        ),
    )
    monkeypatch.setattr(
        sp.subprocess, "check_call", lambda args: called["pip"].append(tuple(args))
    )
    sp.manage_virtual_environment()
    assert called["create"] is True and len(called["pip"]) >= 2


def test_manage_virtual_environment_recreate_existing(monkeypatch, tmp_path: Path):
    """Recreate existing venv when user confirms."""
    monkeypatch.setattr(sp, "VENV_DIR", tmp_path / "venv")
    sp.VENV_DIR.mkdir()
    seq = iter(["y", "y"])  # yes then confirm recreate
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": next(seq))
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    removed = {"ok": False}
    monkeypatch.setattr(sp.shutil, "rmtree", lambda p: removed.__setitem__("ok", True))
    sp.manage_virtual_environment()
    assert removed["ok"] is True


def test_manage_virtual_environment_skip(monkeypatch):
    """Skip venv management when user declines."""
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": "n")
    monkeypatch.setattr(sp, "is_venv_active", lambda: False)
    sp.manage_virtual_environment()


def test_view_program_descriptions_flow(monkeypatch):
    """Describe program 1, then return to main menu."""
    seq = iter(["1", "0"])  # show program 1 then return
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="y": next(seq))
    sp.view_program_descriptions()


def test_parse_cli_args(monkeypatch):
    """Parse CLI args for language and no-venv switch."""
    monkeypatch.setattr(sys, "argv", ["setup_project.py", "--lang", "sv", "--no-venv"])
    args = sp.parse_cli_args()
    assert args.lang == "sv" and args.no_venv is True


# ----- additional setup flows -----
def test_view_logs_with_file_select_by_number(monkeypatch, tmp_path: Path, capsys):
    """Select log file by index, verify file content is displayed."""
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    logf = tmp_path / "ai_processor.log"
    logf.write_text("hello log", encoding="utf-8")
    seq = iter(["1", "0"])  # select first, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.view_logs()
    out = capsys.readouterr().out
    assert "hello log" in out


def test_view_logs_invalid_choice_then_exit(monkeypatch, tmp_path: Path, capsys):
    """Invalid log choice then exit; ensures robust loop handling."""
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    (tmp_path / "x.log").write_text("x", encoding="utf-8")
    seq = iter(["does-not-exist", "0"])  # invalid, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.view_logs()


def test_reset_project_no_files(monkeypatch, tmp_path: Path):
    """Run reset when no files exist; ensures no crash."""
    monkeypatch.setattr(sp, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="n": "n")
    sp.reset_project()


def test_view_logs_numeric_out_of_range(monkeypatch, tmp_path: Path):
    """Out-of-range numeric selection then exit."""
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    (tmp_path / "aa.log").write_text("x", encoding="utf-8")
    seq = iter(["9", "0"])  # out-of-range index, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.view_logs()


def test_reset_project_nested_dirs_removed(monkeypatch, tmp_path: Path):
    """Reset removes nested generated files under data tree."""
    monkeypatch.setattr(sp, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path / "logs")
    nested = tmp_path / "data" / "ai_processed_markdown" / "d1" / "d2"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "f.txt").write_text("1", encoding="utf-8")
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="n": "y")
    sp.reset_project()
    data_dir = tmp_path / "data"
    assert not any(p.is_file() for p in data_dir.rglob("*"))


def test_main_menu_choices(monkeypatch):
    """Exercise each main menu path once and exit."""
    calls = {"env": 0, "desc": 0, "pipe": 0, "logs": 0, "reset": 0}
    monkeypatch.setattr(
        sp,
        "manage_virtual_environment",
        lambda: calls.__setitem__("env", calls["env"] + 1),
    )
    monkeypatch.setattr(
        sp,
        "view_program_descriptions",
        lambda: calls.__setitem__("desc", calls["desc"] + 1),
    )
    monkeypatch.setattr(
        sp,
        "run_processing_pipeline",
        lambda: calls.__setitem__("pipe", calls["pipe"] + 1),
    )
    monkeypatch.setattr(
        sp, "view_logs", lambda: calls.__setitem__("logs", calls["logs"] + 1)
    )
    monkeypatch.setattr(
        sp, "reset_project", lambda: calls.__setitem__("reset", calls["reset"] + 1)
    )
    seq = iter(["1", "2", "3", "4", "5", "6"])  # exercise each menu path then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.main_menu()
    assert calls == {"env": 1, "desc": 1, "pipe": 1, "logs": 1, "reset": 1}


def test_main_menu_quality_suite_success(monkeypatch):
    """Select the full quality suite option and then exit (success path)."""
    import setup_project as sp_local

    class R:
        def __init__(self, code: int):
            self.returncode = code

    seq = iter(["q", "6"])  # run quality suite, then exit
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(sp_local, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp_local.subprocess, "run", lambda *a, **k: R(0))
    sp_local.main_menu()


def test_main_menu_quality_suite_failure(monkeypatch):
    """Select the full quality suite option and then exit (failure path)."""
    import setup_project as sp_local

    class R:
        def __init__(self, code: int):
            self.returncode = code

    seq = iter(["q", "6"])  # run quality suite, then exit
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(sp_local, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp_local.subprocess, "run", lambda *a, **k: R(1))
    sp_local.main_menu()


def test_main_menu_quality_suite_exception(monkeypatch):
    """Force an exception during quality suite run to cover except path."""
    import setup_project as sp_local

    seq = iter(["q", "6"])  # run quality suite, then exit
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(sp_local, "get_python_executable", lambda: sys.executable)

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(sp_local.subprocess, "run", boom)
    sp_local.main_menu()


def test_main_menu_extreme_quality_suite_success(monkeypatch):
    """Select the extreme quality suite (QQ) option and then exit (success path)."""
    import setup_project as sp_local

    class R:
        def __init__(self, code: int):
            self.returncode = code

    seq = iter(["qq", "6"])  # run extreme quality suite, then exit
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(sp_local, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp_local.subprocess, "run", lambda *a, **k: R(0))
    sp_local.main_menu()


def test_main_menu_extreme_quality_suite_failure(monkeypatch):
    """Select the extreme quality suite (QQ) option and then exit (failure path)."""
    import setup_project as sp_local

    class R:
        def __init__(self, code: int):
            self.returncode = code

    seq = iter(["qq", "6"])  # run extreme quality suite, then exit
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(sp_local, "get_python_executable", lambda: sys.executable)
    monkeypatch.setattr(sp_local.subprocess, "run", lambda *a, **k: R(1))
    sp_local.main_menu()


def test_main_menu_extreme_quality_suite_exception(monkeypatch):
    """Force an exception during extreme quality suite run to cover except path."""
    import setup_project as sp_local

    seq = iter(["qq", "6"])  # run extreme quality suite, then exit
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt: next(seq))
    monkeypatch.setattr(sp_local, "get_python_executable", lambda: sys.executable)

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(sp_local.subprocess, "run", boom)
    sp_local.main_menu()


def test_manage_virtual_environment_install_fallback_when_no_lock(
    monkeypatch, tmp_path: Path
):
    """When requirements.lock is missing, fallback to requirements.txt install path is used."""
    import setup_project as sp_local

    # Prepare venv dir and paths
    monkeypatch.setattr(sp_local, "VENV_DIR", tmp_path / "venv_fb")
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    # Ensure lock file path is non-existent
    monkeypatch.setattr(sp_local, "REQUIREMENTS_LOCK_FILE", tmp_path / "no.lock")

    # Create fake python/pip inside venv when created
    def create_with_python(path, with_pip=True):
        bindir = sp_local.get_venv_bin_dir(sp_local.VENV_DIR)
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )
        (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)

    calls = []

    def record(args):
        calls.append(tuple(map(str, args)))

    monkeypatch.setattr(sp_local.subprocess, "check_call", record)
    sp_local.manage_virtual_environment()
    # The second call should be the install command using requirements.txt fallback
    assert any("-r" in c and str(sp_local.REQUIREMENTS_FILE) in c for c in calls)


def test_manage_virtual_environment_prefer_python313(monkeypatch, tmp_path: Path):
    """Prefer python3.13 for venv creation when available (non-pytest path).

    Simulate presence of a python3.13 interpreter and ensure the creation
    path uses it instead of stdlib venv.create.
    """
    import setup_project as sp_local

    vdir = tmp_path / "v313"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")

    # Simulate non-test environment so the code chooses the python3.13 branch
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # Provide a fake python3.13 path
    monkeypatch.setattr(
        sp_local.shutil,
        "which",
        lambda name: "/usr/bin/python3.13" if name == "python3.13" else None,
    )

    created = {"ok": False}

    def fake_check_call(args):
        # On venv creation, create minimal venv structure for later steps
        if "-m" in args and "venv" in args:
            bindir = sp_local.get_venv_bin_dir(vdir)
            bindir.mkdir(parents=True, exist_ok=True)
            (
                bindir / ("python.exe" if sys.platform == "win32" else "python")
            ).write_text("", encoding="utf-8")
            (bindir / ("pip.exe" if sys.platform == "win32" else "pip")).write_text(
                "", encoding="utf-8"
            )
            created["ok"] = True
        # No exception to simulate success for pip commands

    monkeypatch.setattr(sp_local.subprocess, "check_call", fake_check_call)
    # venv.create should not be called when python3.13 is available
    monkeypatch.setattr(
        sp_local.venv,
        "create",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not call")),
    )
    sp_local.manage_virtual_environment()
    assert created["ok"] is True


def test_manage_virtual_environment_win_py_success(monkeypatch, tmp_path: Path):
    """On Windows, prefer 'py -3.13 -m venv' when available (success path)."""
    import setup_project as sp_local

    vdir = tmp_path / "w313"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sp_local.sys, "platform", "win32")
    monkeypatch.setattr(
        sp_local.shutil,
        "which",
        lambda name: "C:/Windows/py.exe" if name == "py" else None,
    )

    called = {"venv": False}

    def fake_check_call(args):
        if args and args[0] == "py":
            bindir = sp_local.get_venv_bin_dir(vdir)
            bindir.mkdir(parents=True, exist_ok=True)
            (bindir / "python.exe").write_text("", encoding="utf-8")
            (bindir / "pip.exe").write_text("", encoding="utf-8")
            called["venv"] = True

    monkeypatch.setattr(sp_local.subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(
        sp_local.venv,
        "create",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not call")),
    )
    sp_local.manage_virtual_environment()
    assert called["venv"] is True


def test_manage_virtual_environment_win_py_fail_fallback(monkeypatch, tmp_path: Path):
    """Windows py launcher path raises, ensure fallback to venv.create occurs."""
    import setup_project as sp_local

    vdir = tmp_path / "wfb"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sp_local.sys, "platform", "win32")
    monkeypatch.setattr(
        sp_local.shutil,
        "which",
        lambda name: "C:/Windows/py.exe" if name == "py" else None,
    )

    def boom(args):
        # Only fail the venv creation via 'py -3.13'; let subsequent pip calls succeed
        if args and args[0] == "py":
            raise RuntimeError("boom")

    monkeypatch.setattr(sp_local.subprocess, "check_call", boom)

    def create_with_python(path, with_pip=True):
        bindir = sp_local.get_venv_bin_dir(vdir)
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / "python.exe").write_text("", encoding="utf-8")
        (bindir / "pip.exe").write_text("", encoding="utf-8")

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)
    sp_local.manage_virtual_environment()


def test_manage_virtual_environment_win_no_py_fallback(monkeypatch, tmp_path: Path):
    """On Windows, when 'py' is not found, fallback to venv.create."""
    import setup_project as sp_local

    vdir = tmp_path / "wfb2"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sp_local.sys, "platform", "win32")
    monkeypatch.setattr(sp_local.shutil, "which", lambda name: None)

    created = {"ok": False}

    def create_with_python(path, with_pip=True):
        bindir = sp_local.get_venv_bin_dir(vdir)
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / "python.exe").write_text("", encoding="utf-8")
        (bindir / "pip.exe").write_text("", encoding="utf-8")
        created["ok"] = True

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()
    assert created["ok"] is True


def test_manage_virtual_environment_no_py313_non_test_fallback(
    monkeypatch, tmp_path: Path
):
    """On non-Windows without python3.13 in PATH and not in test-mode, fallback to venv.create."""
    import setup_project as sp_local

    vdir = tmp_path / "fb313"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sp_local.sys, "platform", "linux")
    monkeypatch.setattr(sp_local.shutil, "which", lambda name: None)

    created = {"ok": False}

    def create_with_python(path, with_pip=True):
        bindir = sp_local.get_venv_bin_dir(vdir)
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / "python").write_text("", encoding="utf-8")
        (bindir / "pip").write_text("", encoding="utf-8")
        created["ok"] = True

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()
    assert created["ok"] is True


def test_main_menu_invalid_then_exit(monkeypatch):
    seq = iter(["x", "6"])  # invalid then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    sp.main_menu()


def test_view_logs_open_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path)
    logf = tmp_path / "err.log"
    logf.write_text("content", encoding="utf-8")
    seq = iter(["1", "0"])  # choose first, then exit
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))

    def bad_open(*a, **k):
        raise OSError("denied")

    monkeypatch.setattr("builtins.open", bad_open)
    sp.view_logs()  # should handle error gracefully


def test_reset_project_unlink_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sp, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(sp, "LOG_DIR", tmp_path / "logs")
    f = tmp_path / "data" / "generated_markdown_from_csv" / "file.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sp, "ask_text", lambda prompt, default="n": "y")

    orig_unlink = Path.unlink

    def flaky_unlink(self):
        if self == f:
            raise OSError("blocked")
        return orig_unlink(self)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    sp.reset_project()  # should log error but continue


def test_set_language_invalid_then_ok(monkeypatch):
    """Invalid choice then accepted English in set_language."""
    prev = sp.LANG
    seq = iter(["x", "1"])  # invalid then English
    monkeypatch.setattr(sp, "ask_text", lambda prompt: next(seq))
    try:
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_set_language_keyboard_interrupt(monkeypatch):
    """KeyboardInterrupt triggers a graceful SystemExit from set_language."""

    def raise_kbd():
        raise KeyboardInterrupt

    monkeypatch.setattr(sp, "ask_text", lambda prompt: raise_kbd())
    with pytest.raises(SystemExit):
        sp.set_language()


def test_run_ai_connectivity_check_interactive_ok(monkeypatch):
    import types

    class FakeCfg:
        def __init__(self):
            self.gpt4o_endpoint = "https://x"
            self.api_key = "k"
            self.request_timeout = 1

    class FakeResp:
        def __init__(self, status, text):
            self.status = status
            self._text = text

        async def text(self):
            return self._text

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSess:
        def __init__(self, *a, **k):
            pass

        def post(self, *a, **k):
            return FakeResp(
                200, '{"choices": [{"message": {"content": "Status: OK"}}]}'
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    fake_mod = types.SimpleNamespace(OpenAIConfig=FakeCfg)
    monkeypatch.setitem(sys.modules, "src.program2_ai_processor", fake_mod)
    fake_aiohttp = types.SimpleNamespace(
        ClientSession=FakeSess, ClientTimeout=lambda total=None: None
    )
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aiohttp)
    assert sp.run_ai_connectivity_check_interactive() is True


def test_run_ai_connectivity_check_interactive_fail(monkeypatch):
    import types

    class FakeCfg:
        def __init__(self):
            self.gpt4o_endpoint = "https://x"
            self.api_key = "k"
            self.request_timeout = 1

    class FakeSess:
        def __init__(self, *a, **k):
            pass

        def post(self, *a, **k):
            class R:
                status = 500

                async def text(self):
                    return "err"

                async def __aenter__(self):
                    return self

                async def __aexit__(self, et, e, tb):
                    return False

            return R()

        async def __aenter__(self):
            return self

        async def __aexit__(self, et, e, tb):
            return False

    fake_mod = types.SimpleNamespace(OpenAIConfig=FakeCfg)
    monkeypatch.setitem(sys.modules, "src.program2_ai_processor", fake_mod)
    fake_aiohttp = types.SimpleNamespace(
        ClientSession=FakeSess, ClientTimeout=lambda total=None: None
    )
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aiohttp)
    assert sp.run_ai_connectivity_check_interactive() is False


def test_manage_virtual_environment_no_venvdir_pip_python_fallback(
    monkeypatch, tmp_path: Path
):
    """Cover branch where pip path is missing and VENV_DIR does not exist (688->692).

    We simulate an active venv with missing pip executable path and a non-existent
    project VENV_DIR, ensuring the code takes the false branch and continues.
    """
    import setup_project as sp_local

    monkeypatch.setattr(sp_local, "is_venv_active", lambda: True)
    # Return a non-existent pip path for the active environment
    monkeypatch.setattr(
        sp_local,
        "get_venv_pip_executable",
        lambda p: tmp_path / "missing" / "pip",
    )
    # Return a non-existent python path to force fallback resolution later
    monkeypatch.setattr(
        sp_local,
        "get_venv_python_executable",
        lambda p: tmp_path / "missing" / "python",
    )
    monkeypatch.setattr(sp_local, "VENV_DIR", tmp_path / "no_venv_here")
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()


def test_manage_virtual_environment_venv_exists_no_python_fallback(
    monkeypatch, tmp_path: Path
):
    """Cover fallback to system python when VENV_DIR exists but python is missing (697->703)."""
    import setup_project as sp_local

    vdir = tmp_path / "vdir"
    vdir.mkdir()
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    seq = iter(["y", "y"])  # yes to manage; yes to recreate
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": next(seq))

    def fake_create(path, with_pip=True):
        # Create venv directory structure without python executable
        (vdir / ("Scripts" if sys.platform == "win32" else "bin")).mkdir(
            parents=True, exist_ok=True
        )

    monkeypatch.setattr(sp_local.venv, "create", fake_create)
    # Ensure get_venv_python_executable returns a non-existent path
    monkeypatch.setattr(
        sp_local,
        "get_venv_python_executable",
        lambda p: vdir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python"),
    )
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()


def test_manage_virtual_environment_restart_with_invalid_lang(
    monkeypatch, tmp_path: Path
):
    """Drive restart branch and cover LANG not in (en, sv) path (742->744)."""
    import setup_project as sp_local

    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    monkeypatch.setattr(sp_local, "LANG", "xx")
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")
    vdir = tmp_path / "rv"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)

    def create_with_python(path, with_pip=True):
        bindir = vdir / ("Scripts" if sys.platform == "win32" else "bin")
        bindir.mkdir(parents=True, exist_ok=True)
        (bindir / ("python.exe" if sys.platform == "win32" else "python")).write_text(
            "", encoding="utf-8"
        )

    monkeypatch.setattr(sp_local.venv, "create", create_with_python)
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    captured = {}

    def fake_execve(exe, argv, env):
        captured["exe"] = exe
        captured["argv"] = argv
        captured["env"] = env
        return None

    monkeypatch.setattr(sp_local.os, "execve", fake_execve)
    sp_local.manage_virtual_environment()
    # Ensure we attempted to execve with --no-venv appended
    assert captured.get("argv") and captured["argv"][-1] == "--no-venv"


def test_entry_point_skip_language_prompt_env(monkeypatch):
    """Cover entry_point branches when no --lang and SETUP_SKIP_LANGUAGE_PROMPT=1 (1448->1451, 1451->1453)."""
    import setup_project as sp_local

    monkeypatch.setattr(sys, "argv", ["setup_project.py", "--no-venv"], raising=False)
    monkeypatch.setenv("SETUP_SKIP_LANGUAGE_PROMPT", "1")
    # set_language should not be called; fail the test if it would be
    monkeypatch.setattr(
        sp_local,
        "set_language",
        lambda: (_ for _ in ()).throw(RuntimeError("should not call")),
    )
    monkeypatch.setattr(sp_local, "ensure_azure_openai_env", lambda: None)
    monkeypatch.setattr(sp_local, "main_menu", lambda: None)
    monkeypatch.setattr(sp_local.sys, "exit", lambda code=0: None)
    sp_local.entry_point()


def test_parse_env_file_with_unmatched_lines(tmp_path: Path):
    """Ensure parse_env_file skips unmatched lines to cover 1269->1267 branch."""
    import setup_project as sp_local

    envp = tmp_path / ".env"
    envp.write_text(
        "# comment\nINVALID LINE\nKEY1=val1\nKEY2='val two'\n",
        encoding="utf-8",
    )
    data = sp_local.parse_env_file(envp)
    assert data.get("KEY1") == "val1" and data.get("KEY2") == "val two"
    assert "INVALID LINE" not in "\n".join([f"{k}={v}" for k, v in data.items()])


def test_manage_virtual_environment_vdir_not_created_then_fallback(
    monkeypatch, tmp_path: Path
):
    """Ensure branch 697->703 triggers when venv.create does not create VENV_DIR.

    We simulate a scenario where VENV_DIR does not exist before and after venv.create,
    forcing the code to skip the 'elif VENV_DIR.exists()' block and hit the fallback.
    """
    import setup_project as sp_local

    vdir = tmp_path / "vnone"
    monkeypatch.setattr(sp_local, "VENV_DIR", vdir)
    monkeypatch.setattr(sp_local, "is_venv_active", lambda: False)
    # Choose to proceed with venv creation
    monkeypatch.setattr(sp_local, "ask_text", lambda prompt, default="y": "y")

    # venv.create does nothing (does not create directory), so VENV_DIR remains absent
    monkeypatch.setattr(sp_local.venv, "create", lambda *a, **k: None)
    # get_venv_python_executable returns a non-existent path
    monkeypatch.setattr(
        sp_local,
        "get_venv_python_executable",
        lambda p: vdir
        / ("Scripts" if sys.platform == "win32" else "bin")
        / ("python.exe" if sys.platform == "win32" else "python"),
    )
    monkeypatch.setattr(sp_local.subprocess, "check_call", lambda *a, **k: None)
    sp_local.manage_virtual_environment()


def test_run_processing_pipeline_program3_no_success_message(monkeypatch):
    """Cover run_processing_pipeline path where program3_success is False (937->exit)."""
    import setup_project as sp_local

    # AI check accepted
    monkeypatch.setattr(sp_local, "ask_confirm", lambda *a, **k: True)
    calls = {"n": 0}

    def step_runner(prompt_key, program_name, program_path, fail_key, ok_key, **kw):
        calls["n"] += 1
        # Return False only on the third step to simulate program 3 failing
        return calls["n"] != 3

    monkeypatch.setattr(sp_local, "_run_pipeline_step", step_runner)
    # Avoid network check side effects
    monkeypatch.setattr(sp_local, "run_ai_connectivity_check_interactive", lambda: True)
    sp_local.run_processing_pipeline()
    assert calls["n"] == 3