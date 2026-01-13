# 📊 Datapipeline för Skolbeskrivningar

[![CI](https://github.com/RoadlakeAnalytics/skoltexter-by-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/RoadlakeAnalytics/skoltexter-by-ai/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/RoadlakeAnalytics/skoltexter-by-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/RoadlakeAnalytics/skoltexter-by-ai/branch/main)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/RoadlakeAnalytics/skoltexter-by-ai/badge)](https://scorecard.dev/viewer/?uri=github.com/RoadlakeAnalytics/skoltexter-by-ai)
[![Mutation Testing](https://img.shields.io/badge/Mutation%20Testing-gated-blueviolet)](.github/workflows/ci.yml)
[![Docstrings](https://img.shields.io/badge/Docstrings-100%25-success)](.github/workflows/ci.yml)
[![Semgrep](https://img.shields.io/badge/Semgrep-gated-important)](https://semgrep.dev/docs/semgrep-ci/)
[![Harden-Runner](https://img.shields.io/badge/Harden--Runner-gated-lightgrey)](https://github.com/step-security/harden-runner)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-informational)](.github/workflows/ci.yml)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![Python 3.14](https://img.shields.io/badge/python-3.14-blue)
![ruff](https://img.shields.io/badge/lint-ruff-informational)
![mypy --strict](https://img.shields.io/badge/types-mypy%20--strict-informational)
![Bandit](https://img.shields.io/badge/security-bandit-informational)
![osv-scanner](https://img.shields.io/badge/deps-osv--scanner-informational)
![gitleaks](https://img.shields.io/badge/protected%20by-gitleaks-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Detta projekt är en datapipeline som omvandlar rå svensk skolstatistik till AI-genererade beskrivningar och genererar en modern, interaktiv webbplats för att bläddra bland skolinformation. Huvudmålet är att göra komplex skoldata tillgänglig och användbar för föräldrar som väljer skolor, samtidigt som det fungerar som en robust grund för avancerade AI-textgenereringsfall.

> Pipeline-demo: Realtidsvideo på under en minut som visar hur `setup_project.py` startas, och sedan körs hela piplinen tills öppning av de färdiga webbsidorna (`output/index.html`).
>
> ![Pipeline Demo](assets/sub1min_pipeline_run.gif)

## 🗂️ Innehållsförteckning

- [🔍 Översikt](#översikt)
- [🧩 Huvudkomponenter](#huvudkomponenter)
- [📁 Projektstruktur](#projektstruktur)
- [⚙️ Förutsättningar](#förutsättningar)
- [🚀 Installation](#installation)
- [▶️ Användning](#användning)
- [🔧 Driftsdetaljer](#driftsdetaljer)
- [📝 Loggning](#loggning)
- [📦 Beroenden](#beroenden)
- [🧪 Testning](#testning)
- [CI-strategi: Lokal validering med fjärrverifiering](#ci-strategi-lokal-validering-med-fjärrverifiering)
- [🔒 CI/CD: Extremt strikt läge](#cicd-extremt-strikt-läge)
- [🧷 Pre-commit: lokala kvalitetsgrindar](#pre-commit-lokala-kvalitetsgrindar)
- [🤖 Byta till en annan LLM](#byta-till-en-annan-llm)
- [🪪 Licens](#licens)

## 🔍 Översikt

Denna pipeline bearbetar svensk skolstatistik genom tre huvudsteg:

1. 📝 **CSV till Markdown**: Läser rå CSV-data och genererar en markdown-fil per skola med hjälp av en mall.
2. 🤖 **AI-förbättring**: Bearbetar varje markdown-fil med Azure OpenAI (GPT-4o) för att skapa förbättrade, föräldrafokuserade beskrivningar.
3. 🌐 **Webbplatsgenerering**: Läser in skolornas koder/namn och AI-genererade beskrivningar, konverterar markdown till HTML och genererar en fristående, interaktiv HTML-webbplats.

---

### 🚀 Rådata till webbplats på mindre än 5 minuter 🚀

Om du redan har en Azure OpenAI-endpoint och har dina tre värden för nyckel, endpoint och modellnamn tillgängliga, kan du nu förvänta dig att köra hela pipelinen inom de närmaste fem minuterna, med hjälp av det guidande `setup_project.py`-programmet, som guidar dig genom processen:

- Konfigurera programmet med rätt värden (valfritt, kan göras manuellt).
- Skapa en virtuell miljö för Python (valfritt - tar 2-3 minuter, men rekommenderas).
- Ta dig tid att läsa korta sammanfattningar för programmen (valfritt).
- Kör pipelinen:
  - Steg ett skapar de 44 Markdown-filerna.
  - Steg två skickar dem till AI och sparar svaren.
  - Steg tre skapar en liten webbplats för att enkelt bläddra bland data (valfritt).
- Nu behöver du öppna den genererade `index.html`-filen i mappen `output` (klicka på den, vilket öppnar webbläsaren - valfritt, men rekommenderas).
- Välj en skola från rullgardinsmenyn (om du inte använder webbläsaren finner du skoltexterna i mappen `data/ai_processed_markdown/`).

> Om du hoppar över den virtuella miljön och har `.env`-filen inställd kan du kunna köra hela pipelinen på mindre än 1 minut. 🚀

## 🧩 Huvudkomponenter

- **📊 Data & Mallar**
  - [`database_school_data.csv`](data/database_data/database_school_data.csv): Huvudsaklig indata-CSV med skolstatistik, identifierare och enkätresultat.
  - [`school_description_template.md`](data/templates/school_description_template.md): Markdown-mall för rapporter per skola.
  - [`ai_prompt_template.txt`](data/templates/ai_prompt_template.txt): Promptmall för Azure OpenAI, specificerar krav för AI-genererade beskrivningar.
  - [`website_template.html`](data/templates/website_template.html): Responsiv HTML-mall för den genererade webbplatsen.

- **🧠 Källkod (`src/`)**
  - [`src/config.py`](src/config.py): Centraliserar alla konstanter, sökvägar och konfiguration.
  - [`src/program1_generate_markdowns.py`](src/program1_generate_markdowns.py): Genererar markdown-filer från CSV.
  - [`src/program2_ai_processor.py`](src/program2_ai_processor.py): Bearbetar markdown-filer med Azure OpenAI, hanterar hastighetsbegränsning och omförsök.
  - [`src/program3_generate_website.py`](src/program3_generate_website.py): Genererar den interaktiva HTML-webbplatsen.

- **🛠️ Orkestrering & Installation**
  - [`setup_project.py`](setup_project.py): Interaktiv, menybaserad CLI för att hantera pipelinen, stödjer språkval, miljöhantering, installation av beroenden, pipelinekörning, loggvisning och återställning av filer.

- **📃 Konfiguration & Miljö**
  - [`.env-example`](.env-example): Mall för nödvändiga Azure OpenAI-miljövariabler.
  - [`.gitignore`](.gitignore): Utesluter känslig data, byggartefakter och genererade utdata.

## 📁 Projektstruktur

```
skoltexter-by-ai/
│
├── data/
│   ├── database_data/
│   │   └── database_school_data.csv
│   └── templates/
│       ├── school_description_template.md
│       ├── ai_prompt_template.txt
│       └── website_template.html
│
├── src/
│   ├── config.py
│   ├── program1_generate_markdowns.py
│   ├── program2_ai_processor.py
│   └── program3_generate_website.py
│
├── setup_project.py
├── .env-example
├── requirements.txt
└── README.md
```

Observera: Under körning skapas resultatmappar och filer, bland annat:

- `data/generated_markdown_from_csv/` (markdown från CSV)
- `data/ai_processed_markdown/` (AI‑förädlade markdown)
- `data/ai_raw_responses/` (råa AI‑svar och fel)
- `output/index.html` (genererad webbplats)
- `logs/` (körloggar)

Mappen `tests/` innehåller en testsvit om 143 tester (100% täckning) som körs med `pytest`.

## ⚙️ Förutsättningar

- 🐍 Python 3.11+
- 🔑 Azure OpenAI API-åtkomst (GPT-4o-distribution)
- 📈 Skolstatistik-CSV i förväntat format (inkluderad)
- 🌐 Internetuppkoppling

## 🚀 Installation

### ✅ Rekommenderat: Interaktiv installation

Kör det interaktiva installationsskriptet och följ menyvalen (stöd för engelska/svenska):

```bash
python setup_project.py
```

När installationsskriptet har installerat beroenden (t.ex. `rich` och `questionary`)
startar det om sig självt inuti den virtuella miljön för att aktivera det förbättrade
gränssnittet automatiskt.

### 🔧 Manuell installation
1. Kopiera `.env-example` till `.env` och fyll i Azure-uppgifterna.
2. Skapa en virtuell miljö och installera beroenden:

```bash
python -m venv venv
source venv/bin/activate
# Reproducerbar, säker installation (låst med SHA256)
pip install --require-hashes -r requirements.lock

# Alternativt, om du behöver uppdatera låsfilen lokalt
# (kräver pip-tools):
#   pip install pip-tools
#   pip-compile --resolver=backtracking --allow-unsafe \
#     --generate-hashes --no-emit-index-url \
#     -o requirements.lock requirements.txt
```
3. Placera din CSV på `data/database_data/database_school_data.csv`.

Säkerställ att CSV-filen följer det förväntade formatet med kolumner för skolstatistik, identifierare och enkätresultat.

## ▶️ Användning

### 🧭 Interaktiv

Använd installationsskriptets meny för att köra hela pipelinen:

```bash
python setup_project.py
```

När du startar pipelinen får du först ett val om att köra ett snabbt AI‑anslutningstest. Det skickar en minimal förfrågan och verifierar att din `.env` och nätverkskonfiguration fungerar. Vid lyckat test fortsätter pipelinen, annars får du ett tydligt felmeddelande och kan åtgärda innan du kör om.

I huvudmenyn finns även kvalitetsflöden:

- `Q` – Kör full lokal kvalitetssvit (samma grindar som i CI).
- `QQ` – Kör EXTREM kvalitetssvit: 100 slumpade pytest‑iterationer, docstrings 100% och mutationstest som grind.

### 🛠️ Manuell

Generera markdown:

```bash
python src/program1_generate_markdowns.py
```

AI-bearbeta markdown:

```bash
python src/program2_ai_processor.py
```

Generera webbplats:

```bash
python src/program3_generate_website.py
```

## 🔧 Driftsdetaljer

- **Indata**: `data/database_data/database_school_data.csv` (skolstatistik)
- **Mallar**: `data/templates/` (markdown, AI-prompt, webbplats)
- **AI-förbättrad markdown-utdata**: `data/ai_processed_markdown/`
- **Rå/misslyckade AI-svar**: `data/ai_raw_responses/`
- **Webbplatsutdata**: `output/index.html`
- **Loggar**: `logs/` (alla huvudsteg loggar detaljerad information)

## 📝 Loggning

Alla huvudsteg loggar till katalogen `logs/` med detaljerad information för felsökning och prestandaövervakning.

| 📄 Loggfil                  | 🧾 Beskrivning                      |
|-----------------------------|-------------------------------------|
| `generate_markdowns.log`    | CSV-bearbetning                     |
| `ai_processor.log`          | Kommunikation med AI-tjänst          |
| `generate_website.log`      | Webbplatsgenerering                  |

## 📦 Beroenden

Från `requirements.txt`:

- pandas
- openpyxl
- aiohttp
- aiolimiter
- python-dotenv
- tqdm
- Jinja2
- markdown2
- rich
- questionary

🧰 Ytterligare standardbibliotek som används: argparse, csv, logging, pathlib, json, re, os, asyncio, typing

För testning och kodkontroll:

- black
- ruff
- mypy
- bandit
- osv-scanner
- cyclonedx-bom
- pip-licenses
- pre-commit
- pytest
- pytest-cov
- xdoctest
- pytest-mock
- pytest-asyncio

Installera alla beroenden med:

```bash
# Föredra hash-låst installation
pip install --require-hashes -r requirements.lock
```

## 🧪 Testning

- Kör hela testsuiten (snabbt läge):

  ```bash
  pytest -q --randomly-seed=1
  ```

- Kör tester med coverage-rapport (visar otäckta rader):

  ```bash
  pytest --randomly-seed=1 \
    --cov=src --cov=setup_project --cov-branch \
    --cov-report=term-missing --cov-report=xml --cov-fail-under=100
  ```

- Kör även en andra gång med annan seed för att upptäcka ordningsberoenden:

  ```bash
  pytest -q --maxfail=1 --randomly-seed=2
  ```

- Extrem testning (100 slumpade iterationer) + mutationstest som grind:

  ```bash
  python tools/run_all_checks.py --extreme
  ```

- Täckningsgrind i CI: 100% och varningar behandlas som fel (se `pytest.ini`).
- Pytest samlar endast tester från `tests/` och ignorerar `mutants/` (artefakter från mutationstestning) för stabil insamling.
- Typkontroll och lint körs i CI. Lokalt kan du köra:

  ```bash
  ruff check .
  mypy --strict src setup_project.py
  ```

- Pre-commit (format, lint, säkerhetskontroller):

  ```bash
  pip install -r requirements.txt
  pre-commit install
  pre-commit run --all-files
  ```

### CI-strategi: Lokal validering med fjärrverifiering

Vår kvalitetsstrategi bygger på principen att fånga fel så tidigt som möjligt. Därför använder vi en omfattande `pre-commit`-svit som kör en fullständig lokal CI/CD-pipeline innan kod kan pushas. GitHub Actions används sedan för att verifiera detta i en ren miljö och för att köra tester som är opraktiska lokalt.

1.  Snabba kontroller (vid Pull Request & Push): För varje kodändring körs ett jobb som exakt speglar vår lokala `pre-commit`-konfiguration. Detta verifierar linting, typning, säkerhet och tester i en neutral miljö och ger feedback inom några minuter.

    - Branch‑push (före PR): En snabb Ubuntu‑matris (Python 3.11–3.14) körs med en enda pytest‑seed för att snabbt ge feedback innan PR öppnas.

2.  Nattlig & Veckovis "Canary"-körning:
    - Dagligen (02:00 UTC): Den fullständiga testsviten körs mot Linux och Windows på alla Python-versioner från 3.11 till 3.14.
    - Veckovis (måndagar 03:00 UTC): Samma fullständiga matris körs mot macOS för att säkerställa plattformsoberoende kompatibilitet och samtidigt spara på kostsamma CI-resurser.

    - Syfte: Dessa schemalagda jobb är designade för att proaktivt upptäcka problem som uppstår över tid, såsom regressioner i beroenden och plattformsspecifika inkompatibiliteter.

## 🔒 CI/CD: Extremt strikt läge

Den här pipelinen är hårt säkrad och reproducerbar. Nedan summeras de viktigaste grindarna som körs i CI (och hur du kör dem lokalt):

- Reproducerbara beroenden (hash‑lås):
  - CI installerar med `pip install --require-hashes -r requirements.lock`.
  - Lokalt: samma kommando rekommenderas. Regenerera låsfil med pip‑tools vid ändringar i `requirements.txt` (se installation ovan).

- Multi‑OS testmatris:
  - CI kör tester på `ubuntu`, `windows`, `macos` och Python `3.11–3.14`.

- Pytest hårt läge:
  - Alla varningar är fel (`pytest.ini: filterwarnings=error`).
  - Testerna körs i slumpad ordning två gånger: seeds `1` och `2`.

- Mutationstester (mutmut):
  - CI fäller bygget om någon mutant överlever.
  - Lokalt: `python tools/ci/mutmut_gate.py` (kör `mutmut` och fäller på överlevare).
  - CI och pre-commit gör en snabb städning (tar bort `mutants/` och cachemappar) innan körning för att undvika artefakt‑påverkan.

- Härdad CI‑miljö:
  - Actions är pinnade till commit‑SHA.
  - `permissions: contents: read` globalt; extra rättigheter endast per jobb vid behov.
  - `step-security/harden-runner` blockerar all oväntad nätverkstrafik.

- Statisk analys och beroendekontroller:
  - Semgrep körs i PRs med regeluppsättningen `p/ci` och fäller på hög allvarlighet.
  - GitHub Dependency Review fäller PR vid sårbara beroenden (hög severitet).
  - Lokalt: `pre-commit run semgrep --hook-stage push --all-files`.

- Docstring‑täckning (interrogate):
  - CI kräver 100% docstring‑täckning.
  - Lokalt: `interrogate -v --fail-under 100 src/`.

- SBOM (CycloneDX):
  - Genereras i CI (från miljön) och laddas upp som artefakt. Vi versionshanterar inte SBOM i repo för att undvika brus och merge‑konflikter.
  - Lokalt: pre‑commit‑hooken provgenererar en temporär SBOM från `requirements.lock` för att verifiera att generationen fungerar. Ingen diff mot repo sker och inga filer skrivs om.
  - I CI:s jobb `validate-local-checks` hoppas SBOM‑hooken för att undvika flakiga jämförelser; själva SBOM:en publiceras i `security`‑jobbet.

Observera: Vi undviker GPL/LGPL i projektets egna beroenden. Semgrep körs via dedikerad pre‑commit‑miljö/CI‑action och påverkar inte runtime‑beroenden.

## 🧷 Pre-commit: lokala kvalitetsgrindar

Installera hooks och aktivera även pre‑push‑steg så att alla tunga grindar körs innan du pushar:

```bash
pip install --require-hashes -r requirements.lock
pre-commit install
pre-commit install --hook-type pre-push

# Fulla grindar på commit-steg (tar längre tid):
pre-commit run --all-files

# Samma grindar kan köras i pre-push-steg (ekvivalent):
pre-commit run --hook-stage pre-push --all-files

# Alternativt, kör allt med ett kommando
python tools/run_all_checks.py

# Extremläge (100x pytest + mutmut)
python tools/run_all_checks.py --extreme
```

Tips:
- Pytest‑körningarna använder `pytest-randomly`; `filterwarnings=error` finns i `pytest.ini`.
- Mutationstest-grinden kör samma logik som i CI via `tools/ci/mutmut_gate.py`.
- Semgrep‑hooken använder konfiguration `p/ci` och fäller på hög severitet.

Notera: Som standard skapas den virtuella miljön med Python 3.13 om den finns installerad; annars används aktuell tolk. Detta speglar projektets fokus på senaste stabila version.

## Byta till en annan LLM

Jag har tagit fram en kort guide för _ungefär_ vad som behöver bytas ut för att använda en annan LLM, se [BYTA_LLM.md](./BYTA_LLM.md).

## 🔐 Säkerhet & Tillförlitlighet

- Lint & Typer: `ruff` (inga varningar) och `mypy --strict` i CI.
- Säkerhetsskanning: `bandit` (MEDIUM+), `osv-scanner` för sårbarheter, och secrets‑skanning via Gitleaks.
- SBOM: Genereras med CycloneDX i CI (`sbom.json`).
- Tester: `pytest` med coverage‑grind i CI; async‑tester med nätverksfakes; timeouter/backoff i runtime.
- Rate limiting & retries: Alla AI‑anrop har limiter + exponentiell backoff; timeouts via `aiohttp.ClientTimeout`.
- Logg‑hygien: Inga API‑nycklar/PII i loggar. Fil‑logg avstängd under tester.
 - Reproducerbarhet: Hash‑låsta installationer från `requirements.lock` med `--require-hashes`. Pre‑commit‑hooks upprätthåller stil och säkerhet lokalt.

Gitleaks körs vid push/PR och schemalagt dagligen (02:00 UTC) samt veckovis (måndagar 03:00 UTC) i samband med de schemalagda körningarna. För organisations‑repo behöver du lägga till en hemlighet `GITLEAKS_LICENSE` under repo/organisationens “Secrets and variables → Actions → Secrets”. För personliga repo behövs ingen licens.

Licens‑allowlist

- Tillåtna: MIT, BSD‑2/3‑Clause, Apache‑2.0, ISC, MPL‑2.0, PSF/Python och liknande permissiva licenser.
- Vi normaliserar licenstexter (t.ex. “MIT License”, “Apache Software License”) till SPDX‑liknande ID:n och hanterar kombinationer som “Apache‑2.0 AND MIT”.
- Kända paket med oklara/varierande licenstexter har explicita overrides (se koden för lista), och meta‑paketet `pre-commit-placeholder-package` ignoreras.
- För att undvika GPL‑beroenden används den icke‑GPL:ade varianten av jsonschema: `jsonschema[format-nongpl]>=4.18` i `requirements.txt`.
- Policyn upprätthålls via pre‑commit och i CI; se `tools/policy/check_licenses.py`.

Kör lokalt:

```bash
pip install -r requirements.txt
pre-commit install
pre-commit run --all-files
# eller endast licenskollen
python tools/policy/check_licenses.py
```

## 🪪 Licens

Detta projekt är licensierat under MIT-licensen.

Se filen [LICENSE](./LICENSE) för fullständiga detaljer.
