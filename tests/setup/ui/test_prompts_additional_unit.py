"""Additional unit tests for ``src.setup.ui.prompts``.

These tests exercise TUI updater behaviour, the optional ``questionary``
adapter paths, and the non‑TTY / EOF fallbacks. Each test uses the
``monkeypatch`` fixture to remain order‑independent and avoids relying on
external optional packages.

"""

from types import SimpleNamespace
import sys

from src.setup import console_helpers as ch
from src.setup.ui import prompts as prom
from src.setup.pipeline import orchestrator


def test_ask_text_tui_updater_and_input(monkeypatch) -> None:
    """Prompt uses TUI updater and returns stripped input.

    This test enables TUI mode and registers a prompt updater. It ensures
    that the prompt updater is invoked with a ``Panel`` and that the
    function returns the stripped result of ``input`` when the test
    environment is active.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to modify environment and builtin input.

    Returns
    -------
    None
    """
    recorded: dict = {}

    def _update_prompt(pan):
        recorded["panel"] = pan

    # Install a lightweight fake orchestrator module in sys.modules so the
    # import inside ``ask_text`` reliably sees our TUI flags regardless of
    # other tests that may reload or modify the real orchestrator module.
    from types import ModuleType

    fake_orch = ModuleType("src.setup.pipeline.orchestrator")
    fake_orch._TUI_MODE = True
    fake_orch._TUI_UPDATER = lambda v: None
    fake_orch._TUI_PROMPT_UPDATER = _update_prompt
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", fake_orch)
    # Ensure the package attribute also points to our fake so "from pkg import sub" works
    if "src.setup.pipeline" in sys.modules:
        monkeypatch.setattr(
            sys.modules["src.setup.pipeline"], "orchestrator", fake_orch, raising=False
        )
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr("builtins.input", lambda prompt="": "  hello  ")
    # Sanity-check that the fake orchestrator is installed and has our flags
    assert sys.modules["src.setup.pipeline.orchestrator"]._TUI_MODE is True
    assert sys.modules["src.setup.pipeline.orchestrator"]._TUI_UPDATER is not None
    assert callable(
        getattr(
            sys.modules["src.setup.pipeline.orchestrator"], "_TUI_PROMPT_UPDATER", None
        )
    )

    out = prom.ask_text("Say hi", default="DEF")
    assert out == "hello"
    # Ensure the updater callback was invoked and recorded the Panel
    assert "panel" in recorded
    panel = recorded["panel"]
    # Panel fallback stores title and renderable attributes.
    assert getattr(panel, "title", "") == "Input"
    assert "Say hi" in str(getattr(panel, "renderable", ""))


def test_ask_text_questionary_branch(monkeypatch) -> None:
    """Questionary adapter is preferred when available.

    The console helper's ``_HAS_Q`` flag is set and a light-weight
    stub for ``questionary.text(...).ask()`` is provided; the return
    value should be stripped and returned by ``ask_text``.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch the console_helpers module.

    Returns
    -------
    None
    """
    # Ensure any TUI mode is disabled so the questionary path is used. Use a
    # fake orchestrator module to avoid interference from other tests.
    from types import ModuleType

    fake_orch2 = ModuleType("src.setup.pipeline.orchestrator")
    fake_orch2._TUI_MODE = False
    fake_orch2._TUI_UPDATER = None
    fake_orch2._TUI_PROMPT_UPDATER = None
    monkeypatch.setitem(sys.modules, "src.setup.pipeline.orchestrator", fake_orch2)
    if "src.setup.pipeline" in sys.modules:
        monkeypatch.setattr(
            sys.modules["src.setup.pipeline"], "orchestrator", fake_orch2, raising=False
        )
    monkeypatch.setattr(ch, "_HAS_Q", True, raising=False)
    monkeypatch.setattr(
        ch,
        "questionary",
        SimpleNamespace(
            text=lambda prompt, default=None: SimpleNamespace(ask=lambda: "  qval  ")
        ),
        raising=False,
    )
    val = prom.ask_text("Prompt?", default="X")
    assert val == "qval"


def test_ask_select_numeric_and_eof(monkeypatch) -> None:
    """Selecting by numeric input and EOF fallback behaviour.

    The function should return the selected choice when a numeric index
    is provided and should return the last choice if ``input`` raises
    ``EOFError``.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to patch input.

    Returns
    -------
    None
    """
    # Ensure questionary is not used and provide numeric selection
    monkeypatch.setattr(ch, "_HAS_Q", False, raising=False)
    monkeypatch.setattr(ch, "questionary", None, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt="": "2")
    out = prom.ask_select("Pick:", ["A", "B", "C"])
    assert out == "B"

    # EOF case: input raises EOFError, expect last choice
    def _raise_eof(prompt=""):
        raise EOFError()

    monkeypatch.setattr("builtins.input", _raise_eof)
    out2 = prom.ask_select("Pick:", ["X", "Y"])
    assert out2 == "Y"


def test_non_tty_behaviour_for_text_and_confirm(monkeypatch) -> None:
    """Non‑TTY and not in test env should return sensible defaults.

    By removing the ``PYTEST_CURRENT_TEST`` environment variable and
    stubbing ``sys.stdin.isatty`` to return False we simulate a daemon
    non‑interactive environment and the functions should return the
    provided defaults.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to modify environment and stdin behaviour.

    Returns
    -------
    None
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    # Only patch the isatty() method on the real stdin so input() still
    # works (StringIO/TextIOBase must provide readline used by input()).
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    # ask_text should return the default when not interactive
    assert prom.ask_text("Q?", default="DF") == "DF"
    # ask_confirm should return the provided default_yes value
    assert prom.ask_confirm("OK?", default_yes=False) is False
