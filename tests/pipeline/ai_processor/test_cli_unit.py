"""Unit tests for AI processor CLI helpers. (unique module name)
"""

import argparse
import asyncio
import logging
from types import SimpleNamespace
from pathlib import Path

import src.pipeline.ai_processor.cli as p2cli


def test_configure_logging_swallows_filehandler_errors(monkeypatch):
    class BadFileHandler:
        def __init__(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setattr(logging, "FileHandler", BadFileHandler)
    # Should not raise despite FileHandler failing
    p2cli.configure_logging(level="DEBUG", enable_file=True)


def test_log_processing_summary(tmp_path: Path, caplog):
    caplog.set_level(logging.INFO)
    md_dir = tmp_path / "md"
    json_dir = tmp_path / "json"
    md_dir.mkdir()
    json_dir.mkdir()
    (md_dir / "a.md").write_text("x")
    (json_dir / "r.json").write_text("{}")

    stats = {
        "total_files_in_input_dir": 1,
        "skipped_already_processed": 0,
        "attempted_to_process": 1,
        "successful_ai_processing": 1,
        "failed_ai_processing": 0,
    }

    p2cli.log_processing_summary(stats, md_dir, json_dir)
    assert "Processing summary" in caplog.text


def test_parse_arguments_defaults(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "argv", ["prog"])
    ns = p2cli.parse_arguments()
    assert hasattr(ns, "limit")
    assert hasattr(ns, "input")
    assert hasattr(ns, "output")
    assert hasattr(ns, "log_level")
    assert hasattr(ns, "lang")


def test_main_handles_openaiconfig_valueerror(monkeypatch, caplog):
    # Patch the package-level OpenAIConfig to raise ValueError when constructed
    import src.pipeline.ai_processor as ai_pkg

    def bad_conf():
        raise ValueError("bad env")

    monkeypatch.setattr(ai_pkg, "OpenAIConfig", bad_conf)
    # Ensure parse_arguments returns a minimal namespace
    monkeypatch.setattr(p2cli, "parse_arguments", lambda: SimpleNamespace(limit=None, input=str(Path.cwd()), output=str(Path.cwd()), log_level="INFO", lang="en"))

    # The important behaviour is that main() does not raise on config errors.
    p2cli.main()



def test_main_uses_asyncio_run_stub(monkeypatch):
    import src.pipeline.ai_processor as ai_pkg

    # Provide a benign OpenAIConfig and Processor
    class Cfg:
        pass

    class FakeProcessor:
        def __init__(self, cfg, inp, out):
            self.cfg = cfg

        async def process_all_files(self, limit=None):
            return None

    monkeypatch.setattr(ai_pkg, "OpenAIConfig", lambda: Cfg())
    monkeypatch.setattr(ai_pkg, "SchoolDescriptionProcessor", FakeProcessor)

    monkeypatch.setattr(p2cli, "parse_arguments", lambda: SimpleNamespace(limit=None, input=str(Path.cwd()), output=str(Path.cwd()), log_level="INFO", lang="en"))

    called = {}

    def stub_run(arg):
        called["ok"] = True

    # Ensure our stub is treated as non-stdlib so main uses the alternate path
    stub_run.__module__ = "stubmod"
    monkeypatch.setattr(asyncio, "run", stub_run)

    p2cli.main()
    assert called.get("ok") is True
