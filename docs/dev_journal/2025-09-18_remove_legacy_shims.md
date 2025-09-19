# 2025-09-18 — Remove legacy top-level scripts and compatibility shims

Status: Work in progress — initial notes and checklist.

Summary
-------
This note documents the high-level steps taken to remove legacy top-level
entrypoint scripts (`program1_generate_markdowns.py`,
`program2_ai_processor.py`, `program3_generate_website.py`) and the old
Textual UI module (`src/ui_textual.py`). The goal is to eliminate
technical debt and rely on a clean package-based architecture under
`src/pipeline/` and `src/setup/ui/`.

Key changes performed so far
- Removed the old top-level entrypoint scripts and replaced them with
  dedicated runner modules under `src/pipeline/*/runner.py`.
- Moved the Textual UI into `src/setup/ui/textual_app.py` and adjusted the
  orchestrator to use a `DashboardContext` that does not reference legacy
  script paths.
- Eliminated compatibility fallbacks that attempted to import
  `src.program2_ai_processor` from various code paths. The OpenAI config
  now reads `PROJECT_ROOT` dynamically from `src.config` so tests may
  override it via monkeypatching `src.config.PROJECT_ROOT`.
- Updated unit tests to import and exercise the new pipeline modules
  directly, removing reliance on the removed top-level modules.

Remaining TODOs (to finish in follow-up)
- Tidy up any residual docstrings or comments that reference the old
  top-level modules (left intentionally for traceability for now).
- Produce a full developer-facing migration guide that explains how to
  run the pipeline now (runners, CI, and how to migrate any external
  automation). This will be written after final verification.

Notes
-----
- Do NOT modify historical dev journals; create new entries instead.
- This document is a working draft and will be expanded when the
  refactor is finalized.
