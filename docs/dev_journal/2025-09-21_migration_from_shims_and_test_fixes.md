2025-09-21 — Migration from shims and test fixes
===============================================

Overview
--------
This dev journal records the work performed to migrate test imports away from
the legacy `src.setup.app` monolith (the "shim"), to stabilize the test
suite, and to introduce a deterministic diagnostic workflow that identifies
failing or hanging tests without blocking a full `pytest` run. The focus has
been on safe, incremental migration: patch a small batch of tests, run the
affected tests in isolation, and then re-run an automated, per-file test
diagnostic to confirm the whole suite remains healthy.

This document describes:

- The shim problem and the migration approach.
- The diagnostic script we created and how it works.
- How we migrated tests in small batches and the patterns used so tests
  remain deterministic.
- Tests and helper changes made during the migration.
- A concise plan for finishing the job and reaching full coverage.

Principles and constraints
--------------------------
- Do not introduce new tech debt: the compatibility shim (`src/setup/app.py`)
  is a temporary adapter to allow incremental migration; the goal is to remove
  it once all tests import the refactored modules directly.
- Work in small batches and verify locally (run single tests or small files
  instead of the whole suite) to avoid long blocking runs.
- Make monkeypatch points deterministic: tests must patch the same module
  object the production code uses (this was the main source of flakiness).

Background: the shim and why it exists
-------------------------------------
Historically the repository exposed a large top-level runner module
(`src.setup.app`) that exported many helpers and global toggles. Tests were
written to monkeypatch attributes on that module (for example
`src.setup.app.ask_text`, `src.setup.app._TUI_MODE`, `src.setup.app.manage_virtual_environment`).

When we refactored the code into smaller modules (e.g. `src/setup/app_ui.py`,
`src/setup/app_prompts.py`, `src/setup/app_venv.py`, `src/setup/app_runner.py`) a
compatibility shim remained to preserve the old import surface. While this
shim made the repository runnable, it had two negative effects:

1. Tests were still relying on the shim as a patch point, which hid the
   opportunity to make tests import the smaller, single-responsibility
   modules directly.
2. Some tests used `importlib.reload` or installed stubs into `sys.modules`
   in ways that resulted in the test monkeypatch and the production module
   being distinct objects — this caused intermittent loops or infinite
   interactive prompts in the test run (the reason for the repeated
   "Select language ... Invalid choice" lines).

Our strategy
------------

1. Keep the shim for compatibility while we migrate tests in small batches.
   The shim is intentionally small and documented — it is a temporary adapter
   and should be removed once all tests are migrated.
2. For each test file referencing `src.setup.app`, replace the import with a
   precise import of the refactored modules it needs. Where tests expect a
   unified `app` namespace and it is costly to change every call-site in a
   single pass, create a small `SimpleNamespace` in the test that maps the
   needed attributes to the refactored modules and register it in
   `sys.modules['src.setup.app']`. This ensures monkeypatches hit the same
   object the production code consults.
3. Validate each patch by running the affected tests in isolation. That
   avoids long blocking runs and makes it practical to iterate quickly.
4. Use an automated, per-file diagnostic script that runs each test file in
   a subprocess and — if a file fails or times out — runs each test node
   (function) separately to identify the failing node(s). The driver sets
   `PYTEST_TEST_TIMEOUT` in the subprocess environment so the `conftest.py`
   alarm timeout is respected consistently.

The diagnostic tool
-------------------

File: `tools/smarter_diagnose_test_hangs.py`

Purpose
~~~~~~~
Run pytest against each test file separately and produce a JSON report.
This approach avoids locking the main process in a long, potentially
interactive `pytest` run and isolates problematic files quickly.

Key features
~~~~~~~~~~~~
- Walks `tests/` and selects files named `test_*.py`.
- Runs `python -m pytest <file>` in a subprocess with a per-target timeout
  (the CLI `--timeout` argument). The subprocess environment receives
  `PYTEST_TEST_TIMEOUT` so `conftest.py`'s alarm/timer uses the same value.
- If a file run fails (non-zero exit code) or times out, the script parses
  the file to enumerate top-level `test_*` functions and test methods inside
  classes and runs each test node individually to surface the failing node.
- For failing nodes the driver captures a short stdout/stderr preview and
  runs simple heuristics to detect interactive patterns (e.g. repeated
  "Invalid choice" lines, `getpass` references, memory kills, etc.).
- Writes a JSON report to `--out` (defaults to
  `tools/smarter_diagnose_results.json`). The driver now removes any
  existing report before starting so repeated runs are easy to compare.

How to run it
~~~~~~~~~~~~~
Prefer running the tool under the project venv Python to ensure the same
interpreter is used as your test runs:

```bash
source venv/bin/activate
venv/bin/python tools/smarter_diagnose_test_hangs.py --tests-dir tests --timeout 30 --out tools/smarter_diagnose_results.json
```

The produced JSON contains per-file entries with status (`PASS`,
`FAIL`, `TIMEOUT`, `SKIPPED_NO_TESTS`) and per-node details for failing files.

Examples of output interpretation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- If a file is `SKIPPED_NO_TESTS`, pytest collected no tests from that
  file; it may contain conditional test generation or be a helper module.
- If a file is `FAIL` and the `items` list shows failing node(s), run the
  failing node directly (the driver has already done that) and inspect the
  `stdout`/`stderr` snippets in the JSON to see if interactive prompts are
  being triggered.

Patterns used to stabilize tests
--------------------------------

1. Replace brittle `import src.setup.app as app` usage in tests with
   explicit imports of the small refactored modules (e.g. `src.setup.app_ui`,
   `src.setup.app_prompts`, `src.setup.app_venv`, `src/setup/app_runner`).

2. If a test needs the full `app` surface (many references), create a
   compact `SimpleNamespace` in the test that maps only the symbols needed
   to the refactored modules and register it as `sys.modules['src.setup.app']`.
   This allows production code that looks up `sys.modules['src.setup.app']`
   to see the patched object and makes `monkeypatch.setattr(app, 'X', ...)`
   effective.

3. When tests expect to reload modules with different `sys.modules`
   entries (import variants tests), use `importlib.util.spec_from_file_location`
   and create a temporary module object so import-time logic runs against
   the manipulated `sys.modules` entries.

4. Avoid running real external tools in tests: stub `subprocess.*`, `venv.create`,
   and any `os.execve` calls. Where tests need to assert that the code attempted
   to call `subprocess`, stub the `subprocess` object and assert the stub was called.

What we changed (high‑level list)
----------------------------------
- Added and hardened `tools/smarter_diagnose_test_hangs.py` (diagnose per-file
  and per-node, export `PYTEST_TEST_TIMEOUT`, clear output file before writing).
- Migrated many tests in `tests/setup/` to import the new modules or to
  create an `app` SimpleNamespace and register it in `sys.modules` so
  monkeypatches work reliably. Example test files migrated:
  - `tests/setup/test_app_wrappers_unit.py`
  - `tests/setup/test_run_full_quality_unit.py`
  - `tests/setup/test_app_manage_venv.py`
  - `tests/setup/test_app_additional_unit.py`
  - `tests/setup/test_app_targeted_unit.py`
  - `tests/setup/test_app_wrappers_more.py`
  - `tests/setup/test_app_additional_branches.py`
  - `tests/setup/test_app_more_cov.py`
  - `tests/setup/test_app_entrypoint_and_misc_unit.py`
  - `tests/setup/test_app_additional_cov.py`
  - `tests/setup/test_setup_project_more_unit.py`

  (These are representative — the process was repeated in small batches.)

- Left a small, documented compatibility adapter in place at
  `src/setup/app.py` to avoid breaking all tests at once. This shim re-exports
  the refactored functions while we migrate tests; it is temporary and the
  plan is to remove it once no test imports `src.setup.app`.

Tests created/modified
----------------------
- Many tests were updated to import the precise refactored modules. When a
  test referenced many `app` symbols we created a `SimpleNamespace` in the
  test and registered it in `sys.modules['src.setup.app']` — this ensured
  that `monkeypatch.setattr(sp, 'X', ...)` and the production code used the
  same object.
- Tests to exercise TUI behavior (tty vs non-tty, getpass vs input, questionary
  fallbacks) were left isolated and made to stub the optional interactive
  dependencies (Rich, questionary). We added small `rich.panel` stubs when a
  test expected a `Panel` to be constructed.

Coverage snapshot and remaining work
-----------------------------------
After the migration and a set of targeted tests, we re-ran the diagnostic
passes and coverage checks. The overall coverage increased but there are
modules that still need targeted unit tests to hit branches. Prioritized
modules to add tests for (based on the coverage output):

- `src/setup/app_pipeline.py` — pipeline wrapper branches and content_updater
- `src/setup/app_runner.py` — entrypoint variants, venv prompt flows
- `src/setup/app_venv.py` & `src/setup/venv_manager.py` — execve/restart
  and pip fallback flows
- `src/setup/azure_env.py` — .env parsing and connectivity fallback
- `src/pipeline/ai_processor/cli.py` — error handling when OpenAIConfig
  raises and `asyncio.run` stubbing

Plan to finish
--------------
Short term (next 1–2 days):

1. Continue migrating remaining test files that still import
   `src.setup.app` into explicit imports or small `app` namespaces.
2. After all tests import concrete modules, delete `src/setup/app.py` and
   run full diagnostics + coverage.
3. Add focused unit tests for the high priority modules listed above. Use
   monkeypatch and small fake modules in `sys.modules` to avoid heavy
   optional deps (Rich, questionary) during unit tests.

Medium term:

1. Split very large files that exceed a single responsibility (for
   example `src/setup/app_pipeline.py` and `src/setup/app_runner.py`) to
   adhere to SRP and keep file sizes under ~350 lines. Write tests for
   the extracted submodules.
2. Add CI checks that run the diagnostic script as a pre-merge step to
   avoid accidental re‑introductions of interactive or environment‑sensitive
   tests.

Risks & caveats
--------------
- Be careful with tests that intentionally exercise import-time code via
  `importlib` and manual module construction. These tests require special
  handling and should be migrated manually (not automatically) to avoid
  subtle differences in global state.
- Avoid swallowing broad `Exception` types in production code unless
  accompanied with logging — we made a few defensive catches to stabilize
  tests (e.g. file writes) but flagged these places as TODOs to ensure we
  do not silence programming errors permanently.

Appendix: useful commands
-------------------------

- Run the per-file diagnostic (recommended):

  ```bash
  source venv/bin/activate
  venv/bin/python tools/smarter_diagnose_test_hangs.py --tests-dir tests --timeout 30 --out tools/smarter_diagnose_results.json
  ```

- Open the JSON report (short):

  ```bash
  python -c "import json;print(json.load(open('tools/smarter_diagnose_results.json'))['summary'])"
  ```

- Run a single test function with extended timeout:

  ```bash
  PYTEST_TEST_TIMEOUT=60 venv/bin/python -m pytest tests/setup/test_app_more_unit.py::test_ask_wrappers_restore_orchestrator_flags -q
  ```

Closing notes
-------------
This migration pattern — small test batches, isolated verification, and a
per-file diagnostic driver — allowed us to stabilize a previously flaky test
suite without aggressive, large-scale changes. The compatibility shim kept
the repository runnable throughout the process; the shim itself is now
temporary infrastructure and should be removed once the migration is
complete and all tests import the refactored modules directly.

If you want I can now:

- Continue the migration automatically in the next batch (patch 4–6 more
  test files and run the diagnostic), or
- Prepare a PR containing the set of deterministic test changes for
  review before applying the remainder.

Tell me which you prefer and I will proceed.

