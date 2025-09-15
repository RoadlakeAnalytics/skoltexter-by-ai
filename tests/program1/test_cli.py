"""CLI and logging tests for program1_generate_markdowns.
"""

import logging
import sys
from pathlib import Path

import pytest

import src.program1_generate_markdowns as p1


def test_configure_logging_filehandler_error(monkeypatch):
    class BadFH:
        def __init__(self, *a, **k):
            raise RuntimeError("fh error")

    monkeypatch.setattr(p1.logging, "FileHandler", BadFH)
    p1.configure_logging("INFO", enable_file=True)

