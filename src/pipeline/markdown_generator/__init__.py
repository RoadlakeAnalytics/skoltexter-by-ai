"""Markdown generator pipeline package.

This module defines the interface for the markdown generation subpipeline
within the School Data Pipeline project. Its primary role is to expose
public API functions for CSV data ingestion, template processing, template
rendering, and context assembly for markdown content generation. This
package serves as a stable and well-documented API surface, re-exporting
selected helpers from sibling modules for external programmatic access.

A consumer (such as a CLI, orchestrator, or notebook) should import only
from this package to consume the markdown generation layer, never reaching
into submodules directly. Strict architectural decoupling is enforced.

The module-level __all__ restricts the public API to functions declared in:
- src/pipeline/markdown_generator/data_loader.py
- src/pipeline/markdown_generator/processor.py
- src/pipeline/markdown_generator/templating.py

All parameters, return types, and exceptions are described at the function
level in their respective modules. No business logic is defined here.

Examples
--------
A typical usage pattern for a pipeline script consuming this API:

>>> from pipeline.markdown_generator import process_csv_and_generate_markdowns, render_template
>>> generated_paths = process_csv_and_generate_markdowns(
...     csv_path="schools.csv",
...     template_path="description.md",
...     output_dir="output"
... )
>>> with open(generated_paths[0], "r") as fh:
...     print(fh.read()[:100])

Notes
-----
This init module exists purely as a stable API boundary for the
markdown generation pipeline. All implementation details are in
the imported submodules.

References
----------
.. [1] School Data Pipeline Project Specification (AGENTS.md),
       Section 3.1-3.2 “Pipeline Architecture and Boundaries”.

"""

from .data_loader import (
    determine_survey_year_for_report,
    get_survey_answer_value,
    get_value_from_row,
    load_school_rows_from_csv,
)
from .processor import build_template_context, process_csv_and_generate_markdowns
from .templating import (
    extract_placeholders_from_template,
    load_template_and_placeholders,
    render_template,
)

__all__ = [
    "build_template_context",
    "determine_survey_year_for_report",
    "extract_placeholders_from_template",
    "get_survey_answer_value",
    "get_value_from_row",
    "load_school_rows_from_csv",
    "load_template_and_placeholders",
    "process_csv_and_generate_markdowns",
    "render_template",
]
