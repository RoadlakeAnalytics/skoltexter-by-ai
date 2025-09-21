"""Extra unit tests for ``src.setup.ui.prompts`` covering remaining branches.

These tests exercise filesystem/TTY and TUI branches that were not yet
covered by the existing suite. They avoid launching any interactive UI by
monkeypatching stdin/getpass/questionary and by installing small stubs for
the orchestrator when needed.
"""

from types import SimpleNamespace
import types
import sys
import builtins

from src.setup import console_helpers as ch
import src.setup.ui.prompts as prom


def test_ask_text_tui_getpass_and_fallback(monkeypatch):
    """TUI mode: getpass succeeds, and when it fails we fall back to input."""
    # Use the real orchestrator module but monkeypatch its TUI flags so
    # the prompts module sees TUI mode enabled for the duration of the test.
    # Ensure imports inside prom.ask_text pick up our stub orchestrator
    # by replacing any pre-existing entries in sys.modules.
    for k in ("src.setup.pipeline.orchestrator", "src.setup.pipeline"):
        if k in sys.modules:
            del sys.modules[k]

    fake_orch = types.ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = True
    fake_orch._TUI_UPDATER = lambda v: None
    fake_orch._TUI_PROMPT_UPDATER = lambda v: None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", fake_orch)

    # Simulate a real TTY and no pytest env so getpass branch is exercised
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)

    # getpass returns value
    import getpass as _gp

    monkeypatch.setattr(_gp, "getpass", lambda prompt="": "gpval", raising=False)
    assert prom.ask_text("P?", default="d") == "gpval"

    # When getpass raises we should fall back to input and then to default on EOF
    def _bad_getpass(prompt=""):
        raise RuntimeError("no tty")

    monkeypatch.setattr("getpass.getpass", _bad_getpass, raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "inpval", raising=False)
    assert prom.ask_text("P?", default="d") == "inpval"

    # And when input raises EOFError default is returned
    monkeypatch.setattr(
        builtins, "input", lambda prompt="": (_ for _ in ()).throw(EOFError())
    )
    assert prom.ask_text("P?", default="dflt") == "dflt"


def test_ask_text_non_tty_not_in_test_returns_default(monkeypatch):
    """When not a TTY and not under pytest the default is returned."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert prom.ask_text("P?", default="xyz") == "xyz"


def test_ask_confirm_non_tty_default_yes(monkeypatch):
    """ask_confirm returns the default when non-tty and not in test env."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert prom.ask_confirm("Proceed?", default_yes=True) is True


def test_ask_select_non_tty_returns_last_choice(monkeypatch):
    """ask_select returns last choice when non-tty and not in test env."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert prom.ask_select("Pick", ["A", "B", "C"]) == "C"


def test_isatty_exception_is_handled(monkeypatch):
    """If sys.stdin.isatty raises, prompts treat that as non-tty gracefully."""

    def _raise():
        raise RuntimeError("nope")

    monkeypatch.setattr(sys.stdin, "isatty", _raise, raising=False)
    # Under pytest this should go to input branch; stub input
    monkeypatch.setattr(builtins, "input", lambda prompt="": "ok", raising=False)
    assert prom.ask_text("Q?", default="d") == "ok"


def test_ask_confirm_questionary_exception_fallback(monkeypatch):
    """When questionary.confirm raises, ask_confirm falls back to input."""

    class Q:
        @staticmethod
        def confirm(prompt, default=True):
            return SimpleNamespace(
                ask=lambda: (_ for _ in ()).throw(RuntimeError("qerr"))
            )

    monkeypatch.setattr(ch, "questionary", Q, raising=False)
    monkeypatch.setattr(ch, "_HAS_Q", False, raising=False)
    # Input returns 'y'
    monkeypatch.setattr(builtins, "input", lambda prompt="": "y", raising=False)
    assert prom.ask_confirm("Proceed?", default_yes=False) is True
