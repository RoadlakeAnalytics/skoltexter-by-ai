"""Tests for `run_full_quality_suite` helper in setup_project.py."""

import subprocess
import setup_project as sp


def test_run_full_quality_suite_success(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: __import__('types').SimpleNamespace(returncode=0))
    sp.run_full_quality_suite()


def test_run_full_quality_suite_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: __import__('types').SimpleNamespace(returncode=1))
    sp.run_full_quality_suite()

