# 2025-09-14 — Test-splits, fullständig avveckling av `tests/_legacy` och kompatibilitets‑shims

Denna journal dokumenterar att all testlogik har flyttats från monolitiska legacy‑moduler till splittrade, modulnära testfiler. Samma principer användes för att dela upp Program 1, Program 2 och Program 3, samt setup_project-programmet.

## Översikt (klart)

- Legacy‑tester från `tests/_legacy/setup_all.py`, `tests/_legacy/setup_rich_dashboard.py`, `tests/_legacy/program1_all.py`, `tests/_legacy/program2_all.py` och `tests/_legacy/program3_all.py` är nu flyttade till målmoduler under `tests/setup/**` och `tests/pipeline/**` enligt definierade mappningar (se sammanfattning nedan).
- Korta stubbar har ersatt legacy‑filerna för att undvika brutna importer under övergången. Alla wrappers i målfiler har ersatts av faktiska testimplementationer.
- `setup_project.py` har kompletterats med shims som exponerar UI‑, venv‑ och pipeline‑funktioner, så att äldre tester kan monkeypatcha som tidigare.

## Program 1 — uppdelning och testflytt (klart)

- Källa: `tests/_legacy/program1_all.py`
- Mål och tester:
  - `tests/pipeline/markdown_generator/test_data_loader.py`
    - `test_get_value_from_row_and_survey_helpers`
    - `test_get_survey_answer_value_fallback`
    - `test_determine_survey_year_for_report_all_missing`
  - `tests/pipeline/markdown_generator/test_processor.py`
    - `test_build_template_context_survey_branch`
    - `test_process_csv_missing_schoolcode_skip`
    - `test_program1_main_happy_path`
    - `test_process_csv_empty_returns_zero`
    - `test_process_csv_write_error`
  - `tests/pipeline/markdown_generator/test_templating.py`
    - `test_extract_placeholders_from_template_basic`
    - `test_render_template_formats_numbers_and_placeholders`
    - `test_load_template_without_placeholders_raises`

## Program 2 — uppdelning och testflytt (klart)

- Redesign: Program 2 delades i tre fokuserade delar under `src/pipeline/ai_processor/`:
  - `client.py` (HTTP‑klient med retry/backoff, JSON‑hantering, ingen fil‑I/O)
  - `processor.py` (filupptäckt, payload, svarstädning, parallell körning m. semafor/ratelimit)
  - `config.py` (`OpenAIConfig` med `.env`/env‑laddning och härledd `gpt4o_endpoint`)
- Tester flyttade (exempel):
  - `tests/pipeline/ai_processor/test_client.py`: klientens felgrenar (429, 500, invalid JSON) och enkel E2E‑lyckopat via stubbar.
  - `tests/pipeline/ai_processor/test_config.py`: saknade nycklar, Azure utan endpoint, .env‑laddning.
  - `tests/pipeline/ai_processor/test_file_handler.py`: mall‑markörer och `_clean_ai_response`‑varianter.
  - `tests/pipeline/ai_processor/test_processor.py`: payload‑byggnad, skip‑gren vid befintligt output, samt passthrough från mockad klient.

## Program 3 — uppdelning och testflytt (klart)

- Källa: `tests/_legacy/program3_all.py`
- Mål och tester:
  - `tests/pipeline/website_generator/test_data_aggregator.py`
    - `test_read_school_csv_missing_file`
    - `test_load_school_data_empty`
    - `test_read_school_csv_bad_columns`
  - `tests/pipeline/website_generator/test_renderer.py`
    - `test_clean_html_output_type_error`
    - `test_write_html_output_errors`
    - `test_write_no_data_html_creates_file`
    - `test_program3_main_generates_html`

## Setup‑lagret — uppdelning och shims (klart)

- Källa: `tests/_legacy/setup_all.py` och `tests/_legacy/setup_rich_dashboard.py`
- Mål och tester (urval):
  - `tests/setup/app.py`: `test_entry_point_basic`
  - `tests/setup/azure_env.py`: env‑parse, prompt/update och AI‑check (tyst/interactive)
  - `tests/setup/i18n.py`: språkbyte, alias och felgrenar
  - `tests/setup/reset.py`: reset‑flöden (tom katalog, nested dirs, unlink/rmdir‑fel)
  - `tests/setup/venv.py`: plattformsberoende venv‑binärvägar, python‑val
  - `tests/setup/venv_manager.py`: venv‑skapande, reinstall, fallback‑vägar, win‑`py`‑path
  - `tests/setup/pipeline/test_orchestrator.py`: `_run_pipeline_step`, plain/rich‑pipeline, TUI‑updater
  - `tests/setup/pipeline/test_run.py`: TUI‑progress‑tolkning
  - `tests/setup/ui/test_basic.py` och `tests/setup/ui/test_layout.py`: Rich‑layout och fallback
  - `tests/setup/ui/test_prompts.py`: questionary‑/input‑helpers
- `setup_project.py` kompletterades för att exponera:
  - UI: `ui_rule`, `ui_header`, `ui_status`, `ui_info`, `ui_success`, `ui_warning`, `ui_error`, `ui_menu`, `ask_text`, `ask_confirm`, `ask_select`, `ui_has_rich`, `Panel`, `Group`, `Table`, `_RICH_CONSOLE`
  - Venv: `get_venv_bin_dir`, `get_venv_python_executable`, `get_venv_pip_executable`, `get_python_executable`, `is_venv_active`
  - Pipeline: `run_program`, `_run_pipeline_step`, `_run_processing_pipeline_plain`, `_run_processing_pipeline_rich`, `_status_label`, samt wrappern `run_processing_pipeline(...)`
  - Konfiguration: `PROJECT_ROOT`, `LOG_DIR`, `SRC_DIR`, `VENV_DIR`, `REQUIREMENTS_FILE`, `REQUIREMENTS_LOCK_FILE`

## Fullständig mappning (sammanfattning)

- Program 1: se avsnittet “Program 1 — uppdelning och testflytt”.
- Program 2: se avsnittet “Program 2 — uppdelning och testflytt”.
- Program 3: se avsnittet “Program 3 — uppdelning och testflytt”.
- Setup: se avsnittet “Setup‑lagret — uppdelning och shims”.

## Avveckling av `tests/_legacy` (klart)

- Samtliga testfunktioner är flyttade och wrappers borttagna i målfilerna.
- `tests/_legacy` har helt tagits bort.
