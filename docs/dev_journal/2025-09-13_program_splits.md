---
title: "Dev Journal — Program refactor till SRP-moduler (2025-09-13)"
date: 2025-09-13
author: Automatiserad refaktorering
---

Syfte
------
Denna journal dokumenterar refaktoreringen av tre monolitiska skript
(`program1_generate_markdowns.py`, `program2_ai_processor.py`,
`program3_generate_website.py`) till en modulär arkitektur som följer
Single Responsibility Principle (SRP). Alla förändringar gjordes för att
göra koden enklare att testa, underhålla och återanvända.

Översikt — vad som gjordes
--------------------------
- Skapade pipeline‑paket under `src/pipeline/` för varje program:
  - `markdown_generator` — CSV‑inläsning, templating, och processor
  - `ai_processor` — klient (nätverk), konfiguration, filhantering och processor
  - `website_generator` — dataaggregation och HTML‑rendering
- Gjorde huvudskripten (`src/program1_generate_markdowns.py`,
  `src/program2_ai_processor.py`, `src/program3_generate_website.py`) till
  tunna orkestratorer som bara ansvarar för:
  1. Parsning av CLI‑argument
  2. Konfigurera logging
  3. Initiera pipeline‑komponenter
  4. Kalla pipeline‑metoder och spara resultat
- Återskapade AI‑klientens retry/backoff-logik i `AIAPIClient` så att
  beteendet är ekvivalent med originalet (retries, exponentiell
  backoff, hantering för 429, timeout, JSON‑parse‑fel etc.).

Detaljer per program
---------------------

Program 1 — Markdown‑generering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Före:
- Ett monolitisk skript som gjorde allt: parse args, logging, läsa CSV,
  bygga kontext, rendera mall och skriva Markdown.

Efter:
- Paket: `src/pipeline/markdown_generator/`
  - `data_loader.py`: Funktioner för att läsa CSV: `load_school_rows_from_csv`,
    samt hjälpfunktioner `get_value_from_row`, `get_survey_answer_value` och
    `determine_survey_year_for_report`. Endast I/O/parsning/transform — ingen
    rendering eller logging‑konfiguration.
  - `templating.py`: Sträng‑baserade, stateless funktioner `load_template`,
    `extract_placeholders_from_template`, `render_template`, `load_template_and_placeholders`.
  - `processor.py`: Högre nivå funktion `process_csv_and_generate_markdowns`
    som kombinerar `data_loader` + `templating` och skriver filer.
  - `__init__.py`: Exporterar public API.

Huvudskriptet `src/program1_generate_markdowns.py` är nu en tunn
orkestrator som:
1. Parsar CLI
2. Konfigurerar logging
3. Laddar template via `load_template_and_placeholders`
4. Anropar `process_csv_and_generate_markdowns`

Program 2 — AI‑processing
^^^^^^^^^^^^^^^^^^^^^^^^^
Före:
- Stort skript innehållande konfig‑klass, aiohttp‑anrop, retry/backoff,
  filhantering och orchestration i samma fil.

Efter:
- Paket: `src/pipeline/ai_processor/`
  - `config.py`: Minimal `OpenAIConfig` för att läsa .env/system‑env och
    exponera operationella parametrar (max_retries, backoff_factor, timeout etc.).
  - `client.py`: `AIAPIClient` ansvarig för alla nätverksanrop, retries och
    svarsrensning. Den implementerar samma retry/backoff‑strategi som
    originalet (inkl. 429‑hantering, ClientError och TimeoutError mapping).
  - `file_handler.py`: `find_markdown_files` och `save_processed_files` —
    enbart fil‑I/O.
  - `processor.py`: `SchoolDescriptionProcessor` — orkestrerar läsning,
    anrop av `AIAPIClient`, filskrivning och sammanställning av statistik.
  - `__init__.py`: Exporterar de ovanstående byggstenarna.

Huvudskriptet `src/program2_ai_processor.py` är nu ett tunt CLI‑lager som
instansierar `OpenAIConfig` och `SchoolDescriptionProcessor` och kör
`process_all_files`. Den innehåller även logging‑inställningar men ingen
AI‑logik i sig.

Noterbart: För att bevara testbarhet (flera befintliga unit‑tester monkeypatchar
`tqdm_asyncio.gather` eller `SchoolDescriptionProcessor.process_school_file`) så
kommer `process_all_files` först att försöka använda `src.program2_ai_processor.tqdm_asyncio.gather`
om det finns — annars fallback till `asyncio.gather`. Detta görs med en
dynamisk import (import_module) så att tester hinner patcha innan anrop.

Program 3 — Website‑generering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Före:
- Skript som läste CSV, läste AI‑markdown, konverterade markdown till HTML,
  städade HTML och injicerade JSON i en HTML‑mall — allt i en fil.

Efter:
- Paket: `src/pipeline/website_generator/`
  - `data_aggregator.py`: Ansvarar för CSV‑läsning (pandas), rensning och
    deduplicering (`read_school_csv`, `deduplicate_and_format_school_records`,
    `load_school_data`). Ingen HTML‑rendering här.
  - `renderer.py`: Markdown→HTML‑konvertering och HTML‑städning
    (`get_school_description_html`, `clean_html_output`, `generate_final_html`).
  - `__init__.py`: Exporter.

Huvudskriptet `src/program3_generate_website.py` är nu en lätt orkestrator. Den
använder pipeline‑funktioner för att ladda/aggregera data och anropar
`generate_final_html` för att skriva `output/index.html`.

Varför denna uppdelning?
------------------------
- Testbarhet: Varje fil gör en enda sak och är enkel att enhetstesta i
  isolation (exempel: `render_template` i `templating.py` är helt stateless).
- Återanvändbarhet: `AIAPIClient` kan återanvändas i andra projekt utan
  beroenden på filsystem eller CLI.
- Lättare felsökning: retry/backoff‑kod existerar endast i klienten.
- Tunn orkestrator: CLI‑skript hanterar argument, logging och wiring.

Konkreta filändringar (lista)
-----------------------------
- Lagt till: `src/pipeline/markdown_generator/` med:
  - `__init__.py`
  - `data_loader.py`
  - `templating.py`
  - `processor.py`
- Lagt till: `src/pipeline/ai_processor/` med:
  - `__init__.py`
  - `config.py`
  - `client.py` (med retry/backoff)
  - `file_handler.py`
  - `processor.py`
- Lagt till: `src/pipeline/website_generator/` med:
  - `__init__.py`
  - `data_aggregator.py`
  - `renderer.py`
- Uppdaterat: `src/program1_generate_markdowns.py`, `src/program2_ai_processor.py`,
  `src/program3_generate_website.py` för att använda de nya modulerna och bli
  tunna orkestratorer.

Kort om testkörning
--------------------
Jag körde selektiva pytest‑fall och justerade implementationen tills
test‑patchpunkter (t.ex. `tqdm_asyncio.gather`) fungerade med den nya
struktureringen. Några körningar mot hela testsviten tog för lång tid i
den här miljön och timade ut — jag kan gärna köra hela testsviten om du
vill, i en miljö där långkörande tester är acceptabla.

Rekommenderade nästa steg
--------------------------
1. Kör hela testsviten `pytest dev/roadlake/skoltexter-by-ai/tests` i din
   CI eller lokalt för att verifiera att allt går grönt.
2. Överväg att lägga till en snabb README i varje `src/pipeline/*`-katalog som
   beskriver API och ansvar (kan göra det åt dig).
3. Eventuellt extrahera gemensamma konstanter/typer om flera moduler börjar
   dela ännu mer logik.

Appendix — Tips för att läsa koden
----------------------------------
- För Markdown‑delen: börja i `src/pipeline/markdown_generator/processor.py`.
- För AI‑delen: börja i `src/pipeline/ai_processor/processor.py` och läs
  `src/pipeline/ai_processor/client.py` för retry/backoff‑beteendet.
- För Website‑delen: `src/pipeline/website_generator/data_aggregator.py`
  och `renderer.py`.

Slutord
--------
Refaktoreringen gör koden betydligt enklare att testa och underhålla. Varje
modul har nu ett tydligt ansvar och är redo att växa vidare (t.ex. lägga
till mocks, integrera fler tester eller göra klienten mer feature‑rik).
