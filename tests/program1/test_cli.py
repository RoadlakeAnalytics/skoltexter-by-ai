"""CLI and logging tests for program1_generate_markdowns."""

import src.pipeline.markdown_generator.runner as p1


def test_configure_logging_filehandler_error(monkeypatch):
    """Test Configure logging filehandler error."""

    class BadFH:
        """Test BadFH."""

        def __init__(self, *a, **k):
            """Test Init."""
            raise RuntimeError("fh error")

    monkeypatch.setattr(p1.logging, "FileHandler", BadFH)
    p1.configure_logging("INFO", enable_file=True)
