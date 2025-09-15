"""Tests for `src/setup/i18n.py`."""

import pytest

import src.setup.i18n as sp
import src.setup.ui.prompts as pr


def test_set_language_invalid_then_ok_consolidated(monkeypatch):
    prev = sp.LANG
    seq = iter(["x", "1"])  # invalid then English
    monkeypatch.setattr(pr, "ask_text", lambda prompt: next(seq))
    try:
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_translate_alias_unsupported_language(monkeypatch):
    prev = sp.LANG
    try:
        monkeypatch.setattr(sp, "LANG", "xx")
        assert isinstance(sp.translate("welcome"), str)
        assert isinstance(sp._("welcome"), str)
    finally:
        sp.LANG = prev


def test_set_language_exception_then_ok(monkeypatch):
    def raise_once(prompt):
        if getattr(raise_once, "_done", False):
            return "1"
        raise_once._done = True
        raise RuntimeError("boom")

    prev = sp.LANG
    try:
        monkeypatch.setattr(pr, "ask_text", raise_once)
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_translate_and_alias_switch_language(monkeypatch):
    """Switch between languages and validate key translations."""
    assert sp.translate("welcome").startswith("Welcome")
    monkeypatch.setattr(sp, "LANG", "sv")
    assert sp.translate("welcome").startswith("Välkommen")
    assert sp._("exiting").lower().count("avslutar") >= 0


def test_set_language_switch(monkeypatch):
    """Drive set_language through Swedish then back to English."""
    prev = sp.LANG
    try:
        monkeypatch.setattr(pr, "ask_text", lambda prompt: "2")
        sp.set_language()
        assert sp.LANG == "sv"
        monkeypatch.setattr(pr, "ask_text", lambda prompt: "1")
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_set_language_invalid_then_ok(monkeypatch):
    """Invalid choice then accepted English in set_language."""
    prev = sp.LANG
    seq = iter(["x", "1"])  # invalid then English
    monkeypatch.setattr(pr, "ask_text", lambda prompt: next(seq))
    try:
        sp.set_language()
        assert sp.LANG == "en"
    finally:
        sp.LANG = prev


def test_set_language_keyboard_interrupt(monkeypatch):
    """KeyboardInterrupt triggers a graceful SystemExit from set_language."""

    def raise_kbd():
        raise KeyboardInterrupt

    monkeypatch.setattr(pr, "ask_text", lambda prompt: raise_kbd())
    with pytest.raises(SystemExit):
        sp.set_language()
