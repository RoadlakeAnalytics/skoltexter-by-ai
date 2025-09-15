# 2025-09-13 - Split of `setup_project.py`

Date: 2025-09-13

Author: Automated refactoring (performed by developer/CI)

## Summary

Denna journalpost dokumenterar en större refaktorering där den tidigare
monolitiska filen `setup_project.py` delades upp i flera små, väldefinierade
moduler för att uppfylla projektets kod‑ och arkitekturprinciper (SRP på
filnivå). Målet var att minska filstorlek, förbättra läsbarhet, göra koden
mer testbar och underlätta framtida underhåll.

## Background

Tidigare innehöll `setup_project.py` nästan all logik: CLI/parsing, TUI‑logik,
pipeline‑orkestrering, virtuell miljöhanteirng och hjälpfunktioner. Filen växte
sig svåröverskådlig (>1000 rader) vilket ökade risken för buggar och gjorde
enhetstester samt granskning svårare.

## Design principles

- Single Responsibility Principle (SRP) på filnivå — varje fil har ett enda,
  väldefinierat ansvar.
- Max ~300–350 rader per fil (400 rader är projektets hårda gräns).
- Undvik cirkulära importer genom lazy imports där det behövs.
- Exponera ett tydligt, välorganiserat publikt API under `src.setup`.

## New modules and responsibilities

Följande högnivåindelning infördes. Alla sökvägar är i repo‑roten.

### UI layer (`src/setup/ui/`):

- `src/setup/ui/__init__.py` — Paketets publika API, exporterar funktioner/typer.
- `src/setup/ui/basic.py` — Enkla UI‑primitiver (rule, header, info, success,
  warning, error, menu).
- `src/setup/ui/prompts.py` — Fråge‑ och bekräftelsefunktioner (ask_text,
  ask_confirm, ask_select). Integrerar med TUI‑adapter via lazy import.
- `src/setup/ui/layout.py` — Rich‑layout‑builder (`build_dashboard_layout`).
- `src/setup/ui/menu.py` — Main‑meny‑looparna (plain och rich dashboard).
- `src/setup/ui/programs.py` — Programbeskrivningar och loggvisning.
- `src/setup/ui/textual_app.py` — Flyttad Textual‑app (tidigare `src/ui_textual.py`).
- `src/setup/ui/textual.py` — Failsafe/lazy shim: ger tydligt fel om `textual`
  inte finns installerat.

### Pipeline layer (`src/setup/pipeline/`):

- `src/setup/pipeline/__init__.py` — Paketets publika API (exporterar
  `run_program`, `run_processing_pipeline` m.fl.).
- `src/setup/pipeline/run.py` — Kör externa program (subprocess) och hanterar
  streaming/progress.
- `src/setup/pipeline/status.py` — Statusetiketter och tabellrendering.
- `src/setup/pipeline/orchestrator.py` — Hög nivå sekvensering av pipeline‑steg.

### Other

- `src/setup/app.py` — Ny applikations‑runner (`run(args)`) som används från
  `setup_project.entry_point()` för att hålla entry‑filen minimal.
- `setup_project.py` — Nu en liten shim/entry som importerar och delegerar.

## Why this structure?

Den nya strukturen gör det enkelt att:

- läsa och förstå varje enskild del utan att behöva bläddra i en stor fil,
- skriva enhetstester för mindre, fokuserade enheter,
- byta ut eller testa beroenden (t.ex. Rich/Textual) utan att påverka
  icke‑relaterad logik (lazy/failsafe import för textuella beroenden),
- återanvända komponenter (t.ex. `build_dashboard_layout`) i andra kontext.

## Backward compatibility

Eftersom projektet byggdes om är målet att använda de nya paketvägarna
framåt. Inga permanenta duplicerande shims lämnades kvar; viktiga funktioner
exponeras via `src.setup.ui` och `src.setup.pipeline`.

## Verification

Följande kontroller gjordes efter refaktorering:

- Import‑smoke test: `import setup_project; import src.setup.ui; import src.setup.pipeline`
  — lyckades i minimal miljö.
- Textual import är optional: import av `src.setup.ui.textual` i en
  miljö utan `textual` ger ett tydligt fel först vid användning.

## Recommended next steps

1. Kör hela testsviten (`pytest`) och fixa eventuella resterande import‑ eller
   monkeypatch‑beroenden i testerna.
2. Uppdatera CI‑konfigurationen så att linting och typkontroller körs på nya
   moduler.
3. Dokumentera API‑kontrakt (t.ex. i README eller en `CONTRIBUTING.md`) för
   nya moduler om det behövs.

## Patch list (major files created/changed)

- `src/setup/ui/` (nytt paket) — `basic.py`, `prompts.py`, `layout.py`,
  `menu.py`, `programs.py`, `textual_app.py`, `textual.py` (shim), `__init__.py`
- `src/setup/pipeline/` (nytt paket) — `run.py`, `status.py`, `orchestrator.py`,
  `__init__.py`
- `src/setup/app.py` — ny app‑runner
- `setup_project.py` — uppdaterad, nu minimal entrypoint

## Example (quick usage)

```py
from src.setup.ui import ui_rule, ask_text
from src.setup.pipeline import run_processing_pipeline

ui_rule('Exempel')
choice = ask_text('Fortsätt? (y/n)')
if choice.lower().startswith('y'):
    run_processing_pipeline()
```

## Contact

För frågor eller synpunkter, kontakta ansvarig för refaktorn.
