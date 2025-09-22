"""Website Generator Pipeline Module.

Summary
-------
Provides the import surface and portfolio-level interface for the website generation pipeline within the school data processing system. This module centralizes the aggregation, formatting, and rendering utilities required for transforming school data into a static, high-quality HTML website.

Extended Description
-------------------
This file is the minimal initializer for the `website_generator` package. By design, it contains no application logic: it only defines the package boundary, imports application-relevant symbols from submodules (`data_aggregator`, `renderer`), and exposes them through the `__all__` list.

It supports strict decoupling from orchestration/UI layers: the pipeline's pure processing logic is accessible independently from any terminal or dashboard controller. All concrete logic resides in child modules, ensuring single-responsibility and maintainable separation of concerns in accordance with AGENTS.md.

System Boundaries
-----------------
- This initializer does not contain any user-facing logic, class definitions, or functions.
- All business logic is implemented in submodules and accessed via named imports.
- Centralizes public API for packages using `from website_generator import ...`.

References
----------
- See `src/pipeline/website_generator/data_aggregator.py` for CSV deduplication, formatting, and school data loading routines.
- See `src/pipeline/website_generator/renderer.py` for HTML conversion and file output helpers.
- For configuration and constants, see `src/config.py`.
- For error taxonomy, see `src/exceptions.py`.

Usage
-----
Recommended for portfolio readers and maintainers:
    >>> from pipeline.website_generator import generate_final_html, load_school_data
    >>> schools = load_school_data("schools.csv")
    >>> html = generate_final_html(schools)
    >>> with open("schools.html", "w") as f:
    ...     f.write(html)
    
This ensures compliance with the pipeline's decoupled architecture and AGENTS.md documentation standards.

"""

from .data_aggregator import (
    deduplicate_and_format_school_records,
    load_school_data,
    read_school_csv,
)
from .renderer import (
    clean_html_output,
    generate_final_html,
    get_school_description_html,
    write_html_output,
    write_no_data_html,
)

__all__ = [
    "clean_html_output",
    "deduplicate_and_format_school_records",
    "generate_final_html",
    "get_school_description_html",
    "load_school_data",
    "read_school_csv",
    "write_html_output",
    "write_no_data_html",
]
