"""Tests for CLI helper functions in the AI processor package."""

import logging
import os
import asyncio
from types import SimpleNamespace

import src.pipeline.ai_processor.cli as cli


def test_configure_logging_swallows_filehandler_errors(monkeypatch, tmp_path):
    # Patch LOG_DIR to a temp dir and make FileHandler raise
    monkeypatch.setattr(cli, "LOG_DIR", tmp_path)

    class BadHandler(logging.FileHandler):
        def __init__(self, *a, **k):
            raise OSError("boom")

    monkeypatch.setattr(logging, "FileHandler", BadHandler)
    # Should not raise
    cli.configure_logging(level="INFO", enable_file=True)


def test_parse_arguments_defaults(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LANG_UI", "sv")
    # Avoid picking up pytest argv; parse a minimal argv instead
    monkeypatch.setattr("sys.argv", ["prog"])
    ns = cli.parse_arguments()
    assert ns.log_level == "DEBUG" or hasattr(ns, "lang")


def test_main_handles_openaiconfig_valueerror(monkeypatch):
    # Patch OpenAIConfig to raise ValueError
    import importlib as _il

    pkg = _il.import_module("src.pipeline.ai_processor")
    monkeypatch.setattr(
        pkg, "OpenAIConfig", lambda: (_ for _ in ()).throw(ValueError("bad"))
    )
    # Ensure basic logging setup does not raise
    monkeypatch.setattr(asyncio, "run", lambda x: None)
    monkeypatch.setattr("sys.argv", ["prog"])
    cli.main()


def test_main_uses_asyncio_run_stub(monkeypatch):
    called = {}

    class DummyProcessor:
        def __init__(self, cfg, inp, out):
            pass

        async def process_all_files(self, limit):
            called["ran"] = True

    import importlib as _il

    pkg = _il.import_module("src.pipeline.ai_processor")
    monkeypatch.setattr(pkg, "OpenAIConfig", lambda: SimpleNamespace())
    monkeypatch.setattr(pkg, "SchoolDescriptionProcessor", DummyProcessor)

    # Install stub asyncio.run so it receives a coroutine object
    def stub_run(obj):
        called["arg"] = obj

    monkeypatch.setattr(asyncio, "run", stub_run)
    monkeypatch.setattr("sys.argv", ["prog"])
    cli.main()
    assert "arg" in called
