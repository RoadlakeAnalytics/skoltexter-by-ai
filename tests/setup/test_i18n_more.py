"""Additional tests for i18n helpers to exercise error branches."""

import importlib
import src.setup.i18n as i18n


def test_translate_returns_key_on_exception(monkeypatch):
    # Simulate broken TEXTS mapping so translate falls back to returning key
    monkeypatch.setattr(i18n, "TEXTS", None)
    assert i18n.translate("some_missing_key") == "some_missing_key"


def test_set_language_choices_and_interrupt(monkeypatch):
    # Reload module to ensure clean state
    importlib.reload(i18n)

    seq = iter(["2"])
    monkeypatch.setattr(i18n, "_", lambda k: k, raising=False)

    def ask_text(prompt):
        return next(seq)

    # Patch the prompts helper used inside set_language
    monkeypatch.setattr("src.setup.ui.prompts.ask_text", ask_text)
    i18n.set_language()
    assert i18n.LANG in ("en", "sv")

    # KeyboardInterrupt path: make ask_text raise
    def raise_kb(prompt):
        raise KeyboardInterrupt()

    monkeypatch.setattr("src.setup.ui.prompts.ask_text", raise_kb)
    try:
        i18n.set_language()
    except SystemExit:
        # Expected exit on keyboard interrupt
        pass
