"""School Data Pipeline package.

This module serves as the root of the School Data Pipeline Python package,
which transforms raw CSV data about schools into a static, interactive HTML
website using an external AI service for textual generation.

The package enforces a strictly decoupled, layered architecture:
the launcher (entrypoint), the orchestrator/UI layer (user experience and
sequencing), and the core pipeline layer (headless data processing). Each
submodule or subpackage is independently executable and designed for
maximum modularity, maintainability, and testability.

Package Structure
-----------------
- `setup/`:
    Orchestration, virtual environment management, interactive UI (Rich/Textual),
    and sequencing of pipeline stages.
- `pipeline/`:
    Self-contained subpackages for Markdown generation, AI processing
    (asynchronous, resilient API communication), and HTML website rendering.
- `config.py`: All configuration constants (paths, timeouts, limits), as UPPER_SNAKE_CASE.
- `exceptions.py`: All robust, project-specific exception classes.

For typical use, import this package as the root or run the pipeline through the orchestrator
(`src/setup/pipeline/orchestrator.py`) or via the launcher (`setup_project.py`).

Notes
-----
- This package provides a clean import namespace and enforces single responsibility per file.
- The pipeline is structured for bounded concurrency, retry logic, and strict validation at all layers.
- All modules conform to strict type annotations, formatting, and comprehensive NumPy-style documentation.

Examples
--------
Basic import pattern:

>>> import src
>>> # See orchestrator or launcher for entrypoints.

"""
