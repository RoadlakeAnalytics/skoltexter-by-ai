"""Additional branch tests for ``src.setup.ui.prompts`` behaviour.

These tests assert fallback behaviour when the optional questionary
adapter raises exceptions and when getpass falls back to input.
"""

import builtins
import sys
from types import SimpleNamespace

from src.setup import console_helpers as ch
from src.setup.ui import prompts as prom


def test_ask_text_questionary_exception_falls_back(monkeypatch) -> None:
    """If the questionary adapter raises, ``ask_text`` falls back to input.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching the console_helpers state and input.

    Returns
    -------
    None
    """
    # Ensure questionary is present but will raise when used
    monkeypatch.setattr(ch, "_HAS_Q", True, raising=False)

    class BadQ:
        @staticmethod
        def text(prompt, default=None):
            class X:
                def ask(self):
                    raise RuntimeError("boom")

            return X()

    monkeypatch.setattr(ch, "questionary", BadQ(), raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "fallback")
    out = prom.ask_text("P?", default="D")
    assert out == "fallback"


def test_ask_confirm_getpass_exception_fallback(monkeypatch) -> None:
    """When getpass fails in TUI mode, confirm falls back to input.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for setting TUI flags and patching getpass/input.

    Returns
    -------
    None
    """
    # Install a fake orchestrator module so the TUI branch is taken. Set
    # the attribute on the package module if present so ``from pkg import"
    # semantics resolve to our fake.
    fake = SimpleNamespace(
        _TUI_MODE=True, _TUI_UPDATER=lambda v: None, _TUI_PROMPT_UPDATER=lambda v: None
    )
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", fake)
    if "src.setup.pipeline" in sys.modules:
        monkeypatch.setattr(
            sys.modules["src.setup.pipeline"], "orchestrator", fake, raising=False
        )
    # Make getpass.getpass raise so the code uses input()
    import getpass

    monkeypatch.setattr(
        getpass,
        "getpass",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("gpfail")),
        raising=False,
    )
    monkeypatch.setattr(builtins, "input", lambda prompt="": "y")
    # Ensure questionary is not used in this test (avoid prompt_toolkit)
    monkeypatch.setattr(ch, "questionary", None, raising=False)
    monkeypatch.setattr(ch, "_HAS_Q", False, raising=False)
    res = prom.ask_confirm("OK?", default_yes=True)
    assert res is True


def test_ask_select_questionary_select_raises(monkeypatch) -> None:
    """When questionary.select raises, selection falls back to numeric input.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching questionary and builtins.input.

    Returns
    -------
    None
    """

    # Provide a questionary stub with select that raises
    class Q:
        @staticmethod
        def select(prompt, choices=None):
            class X:
                def ask(self):
                    raise RuntimeError("nope")

            return X()

    monkeypatch.setattr(ch, "questionary", Q(), raising=False)
    monkeypatch.setattr(ch, "_HAS_Q", False, raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": "1")
    val = prom.ask_select("Pick?", ["A", "B"])
    assert val == "A"
