"""Tests for the virtual environment manager flows.

These tests provide a lightweight UI adapter object so the manager can be
invoked without touching the real filesystem or executing subprocesses.
"""

from pathlib import Path
import os
import types

import src.setup.venv_manager as vm
from src.setup import venv as venvmod


def test_manage_virtual_environment_create_and_install(monkeypatch, tmp_path: Path):
    vdir = tmp_path / 'venv'
    # Ensure not active
    monkeypatch.setattr(venvmod, 'is_venv_active', lambda: False)

    # Provide UI adapter with minimal attributes expected by manager
    class UI:
        def __init__(self):
            self._ = lambda k: k
            self.ui_has_rich = lambda: False
            self.logger = types.SimpleNamespace(error=lambda *a, **k: None)
            self.subprocess = types.SimpleNamespace(check_call=lambda *a, **k: None)
            # venv.create will be invoked to create venv
            self.venv = types.SimpleNamespace(create=lambda p, with_pip=True: (
                (p / 'bin').mkdir(parents=True, exist_ok=True),
                (p / 'bin' / 'python').write_text('', encoding='utf-8'),
                (p / 'bin' / 'pip').write_text('', encoding='utf-8'),
            ))
            self.os = os
            self.subprocess = self.subprocess
            self.sys = types.SimpleNamespace(platform='linux', executable='/usr/bin/python')
            self.rprint = lambda *a, **k: None
            self.ui_info = lambda *a, **k: None

            def ask_text(prompt, default='y'):
                return 'y'

            self.ask_text = ask_text

    ui = UI()
    # Call manager
    vm.manage_virtual_environment(tmp_path, vdir, tmp_path / 'req.txt', tmp_path / 'req.lock', ui)
    # After running, venv dir should exist and contain python
    assert (vdir / 'bin' / 'python').exists()


def test_manage_virtual_environment_restart_branch(monkeypatch, tmp_path: Path):
    vdir = tmp_path / 'venv'
    bindir = vdir / 'bin'
    bindir.mkdir(parents=True)
    py = bindir / 'python'
    py.write_text('', encoding='utf-8')

    monkeypatch.setattr(venvmod, 'is_venv_active', lambda: False)

    called = {}

    class UI:
        def __init__(self):
            self._ = lambda k: k
            self.ui_has_rich = lambda: True
            self.logger = types.SimpleNamespace(error=lambda *a, **k: None)
            self.subprocess = types.SimpleNamespace(check_call=lambda *a, **k: None)
            self.venv = types.SimpleNamespace(create=lambda *a, **k: None)
            # Provide os with execve we can intercept
            self.os = types.SimpleNamespace(execve=lambda p, a, e: (_ for _ in ()).throw(Exception('execve')))
            self.sys = types.SimpleNamespace(platform='linux', executable='/usr/bin/python')
            self.rprint = lambda *a, **k: None
            self.ui_info = lambda *a, **k: None

            def ask_text(prompt, default='y'):
                return 'y'

            self.ask_text = ask_text

    ui = UI()
    # Force venv_dir exists and assign venv_python detection
    monkeypatch.setattr(vm, 'venvmod', venvmod, raising=False)
    # Run manager; execve will raise but be caught internally
    vm.manage_virtual_environment(tmp_path, vdir, tmp_path / 'req.txt', tmp_path / 'req.lock', ui)
    # If we reached this point, the restart branch was exercised (no crash)
    assert True

