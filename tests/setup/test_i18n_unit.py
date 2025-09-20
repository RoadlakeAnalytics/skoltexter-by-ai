"""Unit tests for internationalisation helpers. (unique name)"""

import builtins

import pytest

from src.setup import i18n


def test_translate_and_missing_key(monkeypatch):
    monkeypatch.setattr(i18n, "LANG", "en")
    val = i18n.translate("welcome")
    assert isinstance(val, str) and len(val) > 0
    assert i18n.translate("nonexistent_key") == "nonexistent_key"


def test_set_language_select_sv(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda prompt="": "2")
    i18n.set_language()
    assert i18n.LANG == "sv"


def test_set_language_keyboardinterrupt(monkeypatch):
    def _raise(_=None):
        raise KeyboardInterrupt()

    monkeypatch.setattr(builtins, "input", _raise)
    with pytest.raises(SystemExit):
        i18n.set_language()
