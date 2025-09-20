"""Extra CLI tests for AI processor CLI helpers."""

import asyncio
import logging
from types import SimpleNamespace
from pathlib import Path
import importlib

import src.pipeline.ai_processor.cli as cli


def test_configure_logging_swallows_filehandler_errors(monkeypatch, tmp_path):
    """If creating the file handler raises, configure_logging should not fail."""
    # Monkeypatch FileHandler constructor to raise
    import logging as _logging

    monkeypatch.setattr(_logging, "FileHandler", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    # Should not raise
    cli.configure_logging(level="INFO", enable_file=True)


def test_log_processing_summary_logs_counts(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    md_dir = tmp_path / "md"
    json_dir = tmp_path / "json"
    md_dir.mkdir()
    json_dir.mkdir()
    (md_dir / "a.md").write_text("x")
    (json_dir / "a.json").write_text("x")
    stats = {
        "total_files_in_input_dir": 3,
        "skipped_already_processed": 1,
        "attempted_to_process": 2,
        "successful_ai_processing": 1,
        "failed_ai_processing": 1,
    }
    cli.log_processing_summary(stats, md_dir, json_dir)
    logs = "\n".join(r.getMessage() for r in caplog.records)
    assert "Processing summary" in logs
    assert "Markdown outputs" in logs
    assert "Raw JSON responses" in logs


def test_main_handles_openaiconfig_valueerror(monkeypatch):
    """When OpenAIConfig raises ValueError the CLI main should return early."""
    # Patch parse_arguments to provide simple args
    monkeypatch.setattr(cli, "parse_arguments", lambda: SimpleNamespace(limit=None, input=".", output=".", log_level="INFO"))
    # Patch OpenAIConfig to raise
    mod = importlib.import_module("src.pipeline.ai_processor")
    monkeypatch.setattr(mod, "OpenAIConfig", lambda: (_ for _ in ()).throw(ValueError("bad")))
    # Run main (should not raise)
    cli.main()


def test_main_uses_asyncio_run_stub(monkeypatch):
    """If asyncio.run appears to be the stdlib symbol the code will call it with the processor coroutine.

    We patch asyncio.run with a stub that claims to originate from the
    stdlib by setting its __module__ attribute so the branch is exercised
    without executing the coroutine.
    """
    monkeypatch.setattr(cli, "parse_arguments", lambda: SimpleNamespace(limit=1, input=".", output=".", log_level="INFO"))

    # Provide a dummy OpenAIConfig and SchoolDescriptionProcessor
    mod = importlib.import_module("src.pipeline.ai_processor")
    monkeypatch.setattr(mod, "OpenAIConfig", lambda: SimpleNamespace())

    class FakeProcessor:
        def __init__(self, cfg, inp, out):
            pass

        def process_all_files(self, limit):
            # Regular function used to ensure no coroutine is created.
            return None

    monkeypatch.setattr(mod, "SchoolDescriptionProcessor", FakeProcessor)

    called = {}

    def stub_run(arg):
        called["arg"] = arg

    # Pretend this stub is the real asyncio.run by setting its __module__
    stub_run.__module__ = "asyncio"
    monkeypatch.setattr(asyncio, "run", stub_run)

    cli.main()
    assert "arg" in called
