"""Additional unit tests for :mod:`src.setup.ui.prompts`.

These tests exercise a few remaining branches in the prompt adapter: the
questionary path, the fallback when the adapter raises, and the TUI path
that invokes the prompt updater. They avoid interactive I/O by stubbing
`input` and `getpass` where needed.
"""

from types import SimpleNamespace
import builtins

from src.setup import console_helpers as ch
import src.setup.ui.prompts as prompts


def test_ask_text_questionary_success(monkeypatch) -> None:
    """Return text provided by the questionary adapter.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture for patching module state.

    Returns
    -------
    None
    """
    monkeypatch.setattr(ch, "_HAS_Q", True, raising=False)

    class FakeText:
        def __init__(self, prompt, default=""):
            self.prompt = prompt

        def ask(self):
            return "  qval  "

    monkeypatch.setattr(ch, "questionary", SimpleNamespace(text=lambda p, default="": FakeText(p, default)), raising=False)
    assert prompts.ask_text("Q") == "qval"


def test_ask_text_questionary_raises_fallback_to_input(monkeypatch) -> None:
    """If the questionary adapter raises, fall back to standard input.

    The adapter's `.text()` is made to raise and the builtin `input` is
    stubbed to provide the fallback value.
    """
    monkeypatch.setattr(ch, "_HAS_Q", True, raising=False)
    monkeypatch.setattr(ch, "questionary", SimpleNamespace(text=lambda p, default="": (_ for _ in ()).throw(Exception("boom"))), raising=False)
    monkeypatch.setattr(builtins, "input", lambda prompt="": " fallback ")
    assert prompts.ask_text("Q", default="def") == "fallback"


def test_ask_text_tui_prompt_updater_invoked(monkeypatch) -> None:
    """TUI path invokes the prompt updater and reads from `input` in tests.

    We enable the orchestrator TUI flags and install a small prompt
    updater that captures the passed Panel's title.
    """
    import src.setup.pipeline.orchestrator as orch
    monkeypatch.setattr(orch, "_TUI_MODE", True, raising=False)
    monkeypatch.setattr(orch, "_TUI_UPDATER", lambda *a, **k: None, raising=False)
    captured = {}

    def _pu(panel):
        captured["title"] = getattr(panel, "title", None)

    monkeypatch.setattr(orch, "_TUI_PROMPT_UPDATER", _pu, raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setattr(builtins, "input", lambda prompt="": "  ans  ")

    val = prompts.ask_text("Prompt?")
    assert val == "ans"
    assert captured.get("title") == "Input"

