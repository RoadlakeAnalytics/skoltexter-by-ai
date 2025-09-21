2025-09-21 — Migration from shims and test fixes
=================================================

Overview
--------

This journal entry documents the analysis, rationale, and concrete plan
for removing legacy "shim" modules from the codebase and from the test
suite. It also records the immediate actions taken at the start of the
safe migration (option A chosen by the project owner) and provides a
step‑by‑step migration plan, commands to reproduce, and a recommended
timeline.

Status at start
---------------

- The code was refactored into smaller modules under `src/setup/*`.
- Many tests and parts of the codebase continued to import or monkey‑
  patch a large top‑level module (historically `src.setup.app` or the
  root `setup_project.py`). To keep things working during refactors,
  temporary compatibility "shims" were introduced both in production
  (`src/setup/app.py`) and in tests (a centralized `tests/_app_shim.py`,
  and many per‑test `ModuleType("src.setup.app")` injections).
- These shims worked as short‑term pragmatics, but they became tech
  debt: they hide true dependencies, create global mutable state that
  tests monkeypatch, and make further refactoring costly and brittle.

Why shims were created in the first place
----------------------------------------

- Quick migration: when splitting a monolith into many modules it is
  time‑consuming and risky to update every caller and every test at
  once. A shim lets the old import surface continue to work while the
  implementation moves.
- Test stability: existing tests often patch the top‑level module or
  its attributes. Creating a test shim allows those tests to keep
  working without changing them immediately.

Why the shims are now a problem
-------------------------------

- Implicit global state: tests can silently influence other tests by
  monkeypatching the same module object.
- Import‑time complexity: many tests relied on reloads and the shim's
  `__file__`, causing fragile import ordering and flakiness.
- Hidden coupling: it's harder to see and enforce module boundaries
  when code reads `sys.modules['src.setup.app']` or when tests always
  patch the shim instead of patching the exact dependency.

High‑level objective
--------------------

Remove all shims (both production and test shims), and migrate the
codebase and tests to a clean architecture where:

- Production code imports its concrete helpers explicitly (e.g.
  `from src.setup.app_prompts import ask_text`).
- Tests patch concrete functions/modules (e.g. monkeypatch
  `src.setup.app_prompts.ask_text`) or use focused local test doubles,
  rather than patching a single global module object.

Chosen migration mode: Option A (safe, batch‑wise migration)
---------------------------------------------------------

The project owner chose Option A: perform a careful, step‑by‑step
migration in small batches. This is the recommended approach because
it keeps the repository runnable at every stage and makes debugging
simple when a batch exposes a failure.

Detailed migration plan (step‑by‑step)
------------------------------------

1. Inventory (discovery)
   - Use `rg` to list all references to the legacy import path:
     - `rg "src.setup.app" -n`
     - `rg 'ModuleType("src.setup.app")' -n tests`
   - Categorize files:
     - "production" files that import or read attributes from the shim
     - "test" files that import or inject shim modules

2. Prepare a small centralized test shim (transitional) — OPTIONAL
   - This is only a short‑term convenience if migration will be done
     gradually across many test authors. The long‑term goal is to
     remove *all* test shims. Prefer not to add any new shim.

3. Migrate production modules module‑by‑module
   - For each production file that reads `sys.modules['src.setup.app']`:
     a) Replace dynamic lookups with an explicit import of the concrete
        helper (e.g. `from src.setup.app_prompts import set_language`).
     b) If a direct import causes a circular import, use a lazy import
        inside the function body (import inside function) or extract a
        minimal adapter to break the cycle.
   - Run the small test subset that touches that module.

4. Migrate tests in batches (≈10 files each)
   - For each test file that created an isolated `ModuleType("src.setup.app")`:
     a) Prefer to replace the injection with import of the *concrete*
        module(s) that the test needs, and patch those functions.
     b) If the test truly requires a module object (for import‑time
        behavior), create a local `types.ModuleType("src.setup.app")`
        only in that test's scope and restore state afterwards.
   - Run `pytest` for that file (or the small batch). If the file fails,
     revert the change and mark it for manual refinement.

5. Remove test shims and global fallbacks
   - Once all tests are migrated and green, delete any `tests/_app_shim.py`
     and remove conftest helpers that created shim state.

6. Remove production shim(s)
   - After all production modules import concrete helpers and tests are
     green, delete `src/setup/app.py` and any top‑level propagation code.
   - Run the full test suite and coverage.

7. Clean up and enforce policy
   - Add a small check in CI to detect re‑introductions of the shim
     import path (fail builds if `src.setup.app` is imported in new code).
   - Document the expected testing pattern in CONTRIBUTING.md: tests
     should mock concrete modules, not a shared global module.

Commands & tools
----------------

- Inventory:
  - `rg "src.setup.app" -n`
  - `rg 'ModuleType("src.setup.app")' -n tests`
- Run a single test file:
  - `pytest -q tests/setup/test_xxx.py -q`
- Run a per‑file diagnosis script (we provide one):
  - `python tools/smarter_diagnose_test_hangs.py --tests-dir tests --timeout 30 --out tools/smarter_diagnose_results.json`
- Run whole test suite with coverage:
  - `pytest --cov=src --cov-report=term-missing`

Immediate actions performed (start of Option A)
-----------------------------------------------

1. Created this dev‑journal entry (this file).
2. Removed the centralized test shim that had been used as a long‑term
   workaround (the test suite was subsequently partially migrated).
3. Began migrating tests to use per‑test SimpleNamespace or direct
   imports of concrete modules.

Next batch (what I will execute now)
-----------------------------------

I will proceed with the next migration batch of test files (10 at a time).
Each file will be changed to avoid importing `src.setup.app` and to
patch the concrete `src/setup/*` module(s) instead. After each file I
will run that file's tests in isolation. If a file fails, I will revert
the file and record it in the migration log for manual intervention.

Batch checklist (per file)

- Try to patch the test so it imports the real, concrete module(s).
- Run `pytest -q <file>`.
- If green: commit change (or record in working area).
- If fails: revert and mark for manual fix.

Risks and mitigations
---------------------

- Risk: import‑time tests that rely on `__file__` or reloads are
  fragile. Mitigation: handle these manually by using `importlib.util` to
  load the specific module file or by rewriting the test to avoid reloads.
- Risk: circular imports when replacing lookups with concrete imports.
  Mitigation: use lazy imports inside functions and small adapter modules.
- Risk: accidental reintroduction of new shims. Mitigation: add CI check
  to detect `src.setup.app` imports in new code.

Metrics and goals
-----------------

- Short term: keep test suite runnable and reduce the set of files that
  rely on shims each day.
- Medium term: remove all test shims and `src/setup/app.py` within this
  work stream (target: within a few days of iterative work).
- Long term: add CI guard and update CONTRIBUTING to prevent shim
  reintroductions; increase coverage for modules touched.

Appendix — change log (live)
----------------------------

- 2025-09-21T<now>: This journal entry created. Started batch migration.

---

If you confirm I should proceed I will immediately start the first
controlled batch (10 files) and report results per file. I will also
keep this dev journal updated with a record of every test migration and
any manual decisions that were needed.
