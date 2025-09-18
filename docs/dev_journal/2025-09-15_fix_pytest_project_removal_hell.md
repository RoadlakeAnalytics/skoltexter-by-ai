# Dev Journal — 2025-09-15
## Incident: Pytest triggar radering av projektmappen

Denna journal beskriver ett allvarligt problem där enhetstester i projektet kunde trigga radering av verkliga kataloger i repot (inklusive genererade `data/`, `output/` och `logs/`), varför det hände, hur jag spårade det, vilka förändringar jag gjorde och rekommenderade nästa steg för att förhindra att detta händer igen.

---

## Sammanfattning

- Symptom: När `pytest` kördes kunde ett test orsaka att stora delar av kodbasens filstruktur raderades.
- Påverkade områden: främst `src/setup/` (virtuella miljöhanteraren), samt vissa tester i `tests/setup/` som anropade destruktiva funktioner med osäkra sökvägar.
- Åtgärd: Jag har implementerat runtime‑validering för alla destruktiva raderingsoperationer (centraliserad i `src/setup/fs_utils.py`) och åtgärdat kod- och testfall som skickade osäkra sökvägar. Tester uppdaterades för att använda `tmp_path` och mocka bort faktiska raderingar och nätverksanrop.

---

## Kontext och varför det är viktigt

Projektet är en databehandlingspipeline som genererar filer (markdown, html, milla osv). För att stödja utvecklingsflödet finns en funktionalitet för att rensa genererade artefakter (`reset_project`, och liknande). Sådana funktioner måste vara extremt säkra eftersom felaktiga raderingsanrop lätt kan radera källkod eller användardata.

Följande principer gäller för beslut här: säkra alltid destruktiva operationer i kod, isolera tester (pytest `tmp_path`) och se till att statiska/automatiska analyser (t.ex. semgrep) fångar osäkra mönster.

---

## Hur jag reproducerade och analyserade problemet

1. Jag sökte i repot efter anrop relaterade till destruktiv radering: `reset_project`, `safe_rmtree`, `create_safe_path`, och direkta `shutil.rmtree`-anrop.
2. Jag granskade koden i `src/setup/reset.py`, `src/setup/fs_utils.py` och `src/setup/venv_manager.py` samt tester i `tests/setup/`.
3. Jag observerade ett viktigt mönster:
   - `src/setup/fs_utils.py` definierade `create_safe_path()` som gör strikt validering och en whitelist av vilka kataloger som får raderas.
   - Samtidigt antogs det att `safe_rmtree()` bara tar emot ett redan-validerat `_ValidatedPath` (en `NewType` wrapper) — men detta var en _statisk_ kontrakt (mypy) och inte ett runtime‑säkert krav.
   - I `src/setup/venv_manager.py` fanns ett direkt anrop `safe_rmtree(venv_dir)` i en branch som hanterade ombyggnad av venv. Om ett test råkade skicka exempelvis `Path('.')` eller en tempdir utanför whitelist kunde fel uppstå.
4. Jag hittade även flera tester som skickade osäkra sökvägar (t.ex. `Path('.')`) eller som förlitade sig på att globala `cfg.PROJECT_ROOT` pekade mot en säker plats. Det fanns redan en semgrep‑regel (`unsafe-test-path-usage`) i `.semgrep/project-rules.yml` för detta, vilket bekräftar att detta är en känd risk.

---

## Root cause — detaljerad förklaring

- Problem 1 — bristande runtime‑validering:
  - `safe_rmtree` förlitade sig på att dess argument redan var validerat. Eftersom `NewType(_ValidatedPath, Path)` inte ger runtime‑skydd, fanns inget som hindrade någon från att anropa `safe_rmtree(Path('.'))` och därmed radera godtyckliga kataloger.

- Problem 2 — felaktig uppräckning/antagande i `venv_manager`:
  - `venv_manager` kallade direkt `safe_rmtree(venv_dir)` i recreat‑branchen vilket gjorde att ett osäkert `venv_dir` kunde leda till destruktion utan kontroll.

- Problem 3 — tester skickade osäkra sökvägar:
  - Ett antal tester använde `Path('.')` eller antog att `cfg.PROJECT_ROOT` redan var omdirigerat till testens temporära plats, men några fall gjorde det inte konsekvent.

Kort sagt: en kombination av _antagande om statisk validering_ + _misslyckade test‑isoleringar_ orsakade sårbarheten.

---

## Åtgärder jag implementerade

1. Runtime‑hardening: `safe_rmtree` gör nu alltid validering

   - Fil: `src/setup/fs_utils.py` (`safe_rmtree`)
   - Vad: Innan `shutil.rmtree` anropas görs `create_safe_path(target_path)` på målsökvägen. Om valideringen misslyckas kastas `PermissionError` och raderingen avbryts.
   - Varför: Detta försäkrar att endast whitelisted paths (som definieras centralt i `create_safe_path`) kan raderas — även om en missvisande caller skulle försöka skicka en osäker path.

2. Caller‑fix i venv‑hanteraren

   - Fil: `src/setup/venv_manager.py`
   - Vad: Importerar `venv` som `venvmod` för att göra monkeypatching i tester stabil, och anropar nu explicit `validated = create_safe_path(venv_dir)` följt av `safe_rmtree(validated)` istället för att skicka en oroad `Path` direkt.
   - Varför: Dubbelt skydd — även om `safe_rmtree` nu validerar, är det bra att anropande kod uppför sig korrekt och uttryckligen visar avsikt.

3. Testfixar: isolering och mocking

   - Fil: `tests/setup/test_venv_manager.py`
   - Vad:
     - Ersatte `Path('.')` med `tmp_path` i tester som körde `manage_virtual_environment`.
     - Lagt till `tmp_path` i testsignaturer där det behövdes.
     - Patchade modulen `src.config` (`cfg.PROJECT_ROOT`, `cfg.LOG_DIR`, `cfg.VENV_DIR`) så att alla filoperationer i testfall sker under en temporär katalog.
     - I tester som verifierar att radering försöktes, mockade jag `src.setup.fs_utils.create_safe_path` och `src.setup.fs_utils.safe_rmtree` för att observera beteendet utan att faktiskt radera på disken.
     - Mockade `subprocess.check_call` i tester som annars skulle försöka köra `pip install` och göra nätverksanrop (vilket vi inte vill i unit tests).

   - Varför: Tester måste vara deterministiska och säkra — inga tester ska påverka projektets verkliga filer.

4. Mindre städ och kompatibilitetsjusteringar

   - Lade till `import setup_project as sp` i testfilen där `sp` användes.
   - Rullade igenom kodbasen och sökte efter direkta `shutil.rmtree`/`os.remove`/`os.unlink` utanför `src/setup/fs_utils.py` och bekräftade att inga andra direkta destruktiva anrop fanns.

---

## Exempel (före/efter, förenklat)

Före (förenklat):

```py
# src/setup/venv_manager.py (tidigare)
try:
    safe_rmtree(venv_dir)   # <= farligt: ingen runtime-validering
except PermissionError:
    ...
```

Efter (förenklat):

```py
from .fs_utils import create_safe_path, safe_rmtree

try:
    validated = create_safe_path(venv_dir)
    safe_rmtree(validated)
except PermissionError:
    ...
```

Och i `src/setup/fs_utils.py` säkerställs nu att `safe_rmtree` kör `create_safe_path` om argumentet inte redan validerats.

---

## Verifiering och tester

Jag körde ett antal selektiva testfall och valideringar lokalt efter ändringen:

- `pytest -q tests/setup/test_reset.py::test_reset_project_nested_dirs_removed` — OK
- `pytest -q tests/setup/test_venv_manager.py::test_manage_virtual_environment_remove_error` — OK
- `pytest -q tests/setup/test_venv_manager.py::test_manage_virtual_environment_recreate_existing` — OK

Observera: jag har inte kört hela testsviten i denna session (vissa testfall kräver ytterligare mockar eller CI‑inställningar). Målet i denna omgång var att säkra raderingsbanan och patcha de mest kritiska testen så att de inte längre kan radera repo‑innehåll.

---

## Rekommendationer och nästa steg

1. CI / semgrep
   - Aktivera `.semgrep/project-rules.yml` som ett blockerande steg i CI så att mönster som `manage_virtual_environment(..., Path("."), ...)` eller direkta `shutil.rmtree` utanför `src/setup/fs_utils.py` blockeras i PRs.

2. Policy: explicit tillåt flagga
   - Överväg att kräva en uttrycklig flagga eller environment variable för alla destruktiva operationer i produktionskörning (t.ex. `ALLOW_DESTRUCTIVE_ACTIONS=1`) samt en extra bekräftelse i interaktivt läge. Detta ger ytterligare skydd mot mänskliga misstag.

3. API‑förbättring (valfritt)
   - Alternativt kan `reset_project()` göras tydligare genom att acceptera `project_root: Path` som argument istället för att läsa från global `cfg.PROJECT_ROOT`. Detta gör det svårare för kod att oavsiktligt radera fel katalog utan att explicit ange en root.

4. Test‑hygien
   - Gå igenom `tests/` och säkerställ att alla tester som interagerar med filsystemet använder `tmp_path` eller mockar `src.setup.fs_utils`‑funktioner.
   - Lägg till ett litet test‑fall som kontrollerar att `create_safe_path(Path(PROJECT_ROOT))` kastar `PermissionError` (detta är en regressionskontroll för säkerheten).

5. Dokumentation
   - Lägg till en kort policy i `CONTRIBUTING.md` (eller liknande) som uttryckligen instruerar utvecklare att aldrig köra tester som ändrar filer i repo root och att använda `tmp_path` i tests.

---

## Changelog (patch‑sammandrag)

- `src/setup/fs_utils.py` — hardening: `safe_rmtree` validerar nu målsökvägen med `create_safe_path` innan radering.
- `src/setup/venv_manager.py` — använder `venv` som `venvmod`, validerar `venv_dir` före radering.
- `tests/setup/test_venv_manager.py` — använder `tmp_path`, mockar `fs_utils` och `subprocess` där det behövs.

---

## Appendix: praktiska kommandon

- Kör ett enda test: `pytest -q tests/setup/test_reset.py::test_reset_project_nested_dirs_removed`
- Kör semgrep‑kontroll: `semgrep --config .semgrep/project-rules.yml`
- Sök direkt-raderingsanrop i koden: `rg "shutil.rmtree\(|os.remove\(|os.unlink\(|os.rmdir\(" src -n`

---

Om du vill kan jag nu:

- köra hela testsviten och iterera vidare för att städa kvarvarande test‑fel, eller
- göra en PR‑sammanställning med en koncis commit‑rubrik och beskrivning, och/eller
- lägga in ett CI‑jobb som kör semgrep och blockerar PRs med dessa mönster.

Säg vilket av följande du vill jag prioriterar härnäst: full testkörning, PR‑förberedelser, eller CI‑konfiguration.
