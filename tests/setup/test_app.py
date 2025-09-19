"""Tests for `src/setup/app.py` runner."""

import sys
from types import SimpleNamespace

import src.setup.app as app
import src.setup.i18n as i18n
import src.setup.ui.menu as menu


def test_entry_point_basic(monkeypatch):
    """Test Entry point basic."""
    # Run entry_point with --lang en and --no-venv to cover the flow
    # Avoid interactive pauses and ensure the app runner receives CLI args.
    monkeypatch.setattr(
        sys, "argv", ["setup_project.py", "--lang", "en", "--no-venv"], raising=False
    )
    # Prevent side-effects from interactive helpers
    monkeypatch.setattr(i18n, "set_language", lambda: None, raising=False)
    monkeypatch.setattr(menu, "main_menu", lambda: None, raising=False)
    monkeypatch.setattr(app, "ensure_azure_openai_env", lambda: None, raising=False)
    # Avoid exiting the test process
    monkeypatch.setattr(sys, "exit", lambda code=0: None, raising=False)
    # Run the app entry with a SimpleNamespace simulating parsed args
    app.run(SimpleNamespace(lang="en", no_venv=True))
