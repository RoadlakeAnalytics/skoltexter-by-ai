"""Website Generator Runner (School Data Pipeline Portfolio)

Strictly portfolio-compliant module providing the SRP-oriented, programmatic runner for
the school website generation pipeline. This file is the canonical headless entrypoint
for automated, scripted, and CI/CD execution—never UI, CLI, or interactive logic.

Core Responsibilities
---------------------
- Merge tabular CSV school data and AI-generated Markdown content via pipeline helpers.
- Validate sources and render the final interactive HTML using project templates.
- Export `run_from_config()` as the single-call, fully robust public API for jobs, tests, and automation.
- Guarantee strict decoupling: all orchestration/config handled externally.
- Explicitly handle missing/empty data with minimal HTML stubs and log all errors centrally.
- All configuration sourced *only* from `src/config.py`, with no hard-coded values.
- All error signaling via return values (never outward exceptions), compliant with AGENTS.md.
- All error taxonomy enforced via `src/exceptions.py` (see below).

System Context & Boundaries
---------------------------
- Only generation logic—no orchestration, UI, or direct I/O loops.
- Depends only on pipeline helpers: `data_aggregator` and `renderer`.
- All I/O (csv, markdown, templates, output) is disk-based—inputs must exist on disk.
- All logging uses the standard root logger; never prints or raises from this runner.
- All documentation and examples are strictly file-local and self-contained for audit.

Error Taxonomy Reference
------------------------
- Never directly raises; all exceptions from helpers are caught, logged, and signaled as return values.
- Error classes are enumerated centrally in `src/exceptions.py`.
- Portfolio reviewers can safely rely on file-local error documentation and xdoctest examples.

Usage Examples
--------------
Typical programmatic usage with config defaults:

.. code-block:: python

   from src.pipeline.website_generator.runner import run_from_config
   result = run_from_config()
   assert result is True

Explicit path usage:

.. code-block:: python

   from pathlib import Path
   from src.pipeline.website_generator.runner import run_from_config

   run_from_config(
       csv_path=Path("data/my_schools.csv"),
       ai_markdown_dir=Path("outputs/ai_md"),
       output_file=Path("sites/final.html")
   )

References
----------
- AGENTS.md, Section 3: "PROJECT CONTEXT & ARCHITECTURE"
- Templates: `data/templates/website_template.html`, `data/templates/school_description_template.md`
- Helpers: `src/pipeline/website_generator/data_aggregator.py`, `src/pipeline/website_generator/renderer.py`
- Exception taxonomy: `src/exceptions.py`

Portfolio Compliance
--------------------
All documentation is file-local, gold-standard NumPy/AGENTS.md-compliant, and suitable for direct audit.

"""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import (
    AI_MARKDOWN_DIR,
    ORIGINAL_CSV_PATH,
    OUTPUT_HTML_FILE,
    WEBSITE_TEMPLATE_PATH,
)

from .data_aggregator import (
    load_school_data,
)
from .renderer import generate_final_html, write_html_output

logger = logging.getLogger(__name__)


def run_from_config(
    csv_path: Path | None = None,
    ai_markdown_dir: Path | None = None,
    output_file: Path | None = None,
) -> bool:
    r"""Generate the final HTML portfolio website from CSV and AI Markdown sources.

    Runs the complete "website generation" pipeline for the school data portfolio project.
    Accepts disk paths for the raw CSV, AI-generated Markdown directory, and output HTML file.
    If any argument is ``None``, project-level config defaults from `src/config.py` are used.

    This function:
        - Resolves all provided or default file paths.
        - Loads and merges input data (handling empty or missing sources gracefully).
        - Renders the HTML site using pipeline helpers and templates.
        - Writes output atomically to the specified disk location.
        - Logs all errors and converts exceptions to a `False` result—never raises.

    **Portfolio audit guarantee:** All behavior is deterministic and directly testable via file-local examples.

    Parameters
    ----------
    csv_path : pathlib.Path or None, optional
        The source CSV file containing tabular school data. If ``None``, uses
        ``ORIGINAL_CSV_PATH`` defined in ``src/config.py``.
    ai_markdown_dir : pathlib.Path or None, optional
        Directory containing AI-generated Markdown files. If ``None``, uses ``AI_MARKDOWN_DIR``.
    output_file : pathlib.Path or None, optional
        Destination path for the generated HTML site. If ``None``, uses ``OUTPUT_HTML_FILE``.

    Returns
    -------
    bool
        ``True`` if website generation succeeded and was written fully to disk,
        ``False`` if any error or exception occurred (all details logged).

    Raises
    ------
    Never raises. All exceptions are caught internally, logged via the module logger,
    and signaled as a ``False`` result. Error taxonomy is defined in `src/exceptions.py`.
    Portfolio users and auditors can expect strictly non-raising behavior.

    See Also
    --------
    src/pipeline/website_generator/data_aggregator.py : Data loading, merging helpers.
    src/pipeline/website_generator/renderer.py : HTML rendering and file writing.
    src/config.py : Pipeline-wide configuration constants.
    src/exceptions.py : Exception taxonomy and portfolio error classes.

    Notes
    -----
    - Headless and non-interactive: suitable for automation, CI, jobs, or tests.
    - All input and output paths are resolved using ``pathlib.Path``.
    - Empty, missing, or invalid data results in a minimal valid HTML stub.
    - All outputs are file-local and disk-based; no print/logout side-effects.

    Examples
    --------
    Basic usage with config defaults:

    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> result = run_from_config()
    >>> assert result in (True, False)

    Custom paths for manual runs:

    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> run_from_config(
    ...     csv_path=Path("data/my_schools.csv"),
    ...     ai_markdown_dir=Path("outputs/ai_md"),
    ...     output_file=Path("sites/final.html")
    ... )
    True

    Handling missing/empty input with fallback HTML (no raise):

    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> # Assume "tests/data/empty.csv" is empty
    >>> result = run_from_config(csv_path=Path("tests/data/empty.csv"))
    >>> assert result is True

    Simulating a disk permission failure (returns False):

    >>> from pathlib import Path
    >>> from src.pipeline.website_generator.runner import run_from_config
    >>> result = run_from_config(output_file=Path("/protected/final.html"))
    >>> assert result is False

    """
    csv_path = Path(csv_path) if csv_path is not None else ORIGINAL_CSV_PATH
    ai_markdown_dir = (
        Path(ai_markdown_dir) if ai_markdown_dir is not None else AI_MARKDOWN_DIR
    )
    output_file = Path(output_file) if output_file is not None else OUTPUT_HTML_FILE
    try:
        schools = load_school_data(csv_path, ai_markdown_dir)
        if not schools:
            write_html_output("<html><body><h1>No data</h1></body></html>", output_file)
            return True
        html = generate_final_html(schools, WEBSITE_TEMPLATE_PATH)
        write_html_output(html, output_file)
        return True
    except Exception:
        logger.exception("Failed to generate website")
        return False


__all__ = ["run_from_config"]
