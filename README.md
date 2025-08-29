# 📊 Datapipeline för Skolbeskrivningar

Detta projekt är en datapipeline som omvandlar rå svensk skolstatistik (CSV) till AI-förbättrade beskrivningar och genererar en modern, interaktiv webbplats för att bläddra bland skolinformation. Huvudmålet är att göra komplex skoldata tillgänglig och användbar för föräldrar som väljer skolor, samtidigt som det fungerar som en robust grund för avancerade AI-textgenereringsfall.

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
  - `data/database_data/database_school_data.csv`: Huvudsaklig indata-CSV med skolstatistik, identifierare och enkätresultat.
  - `data/templates/school_description_template.md`: Markdown-mall för rapporter per skola.
  - `data/templates/ai_prompt_template.txt`: Promptmall för Azure OpenAI, specificerar krav för AI-genererade beskrivningar.
  - `data/templates/website_template.html`: Responsiv HTML-mall för den genererade webbplatsen.

- **🧠 Källkod (`src/`)**
  - [`src/config.py`](src/config.py): Centraliserar alla konstanter, sökvägar och konfiguration.
  - [`src/program1_generate_markdowns.py`](src/program1_generate_markdowns.py): Genererar markdown-filer från CSV.
  - [`src/program2_ai_processor.py`](src/program2_ai_processor.py): Bearbetar markdown-filer med Azure OpenAI, hanterar hastighetsbegränsning och omförsök.
  - [`src/program3_generate_website.py`](src/program3_generate_website.py): Genererar den interaktiva HTML-webbplatsen.

- **🛠️ Orkestrering & Installation**
  - `setup_project.py`: Interaktiv, menybaserad CLI för att hantera pipelinen, stödjer språkval, miljöhantering, installation av beroenden, pipelinekörning, loggvisning och återställning av filer.

- **📃 Konfiguration & Miljö**
  - `.env-example`: Mall för nödvändiga Azure OpenAI-miljövariabler.
  - `.gitignore`: Utesluter känslig data, byggartefakter och genererade utdata.

## 📁 Projektstruktur

```
school-description-processor/
│
├── data/
│   ├── database_data/
│   │   └── database_school_data.csv
│   ├── templates/
│   │   ├── school_description_template.md
│   │   ├── ai_prompt_template.txt
│   │   └── website_template.html
│   ├── generated_markdown_from_csv/
│   ├── ai_processed_markdown/
│   └── ai_raw_responses/
│
├── logs/
│
├── output/
│   └── index.html
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

## ⚙️ Förutsättningar

- 🐍 Python 3.7+
- 🔑 Azure OpenAI API-åtkomst (GPT-4o-distribution)
- 📈 Skolstatistik-CSV i förväntat format
- 🌐 Internetuppkoppling

## 🚀 Installation

### ✅ Rekommenderat: Interaktiv installation

Kör det interaktiva installationsskriptet och följ menyvalen (stöd för engelska/svenska):

```bash
python setup_project.py
```

### 🔧 Manuell installation
1. Kopiera `.env-example` till `.env` och fyll i Azure-uppgifterna.
2. Skapa en virtuell miljö och installera beroenden:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Placera din CSV på `data/database_data/database_school_data.csv`.

Säkerställ att CSV-filen följer det förväntade formatet med kolumner för skolstatistik, identifierare och enkätresultat.

## ▶️ Användning

### 🧭 Interaktiv

Använd installationsskriptets meny för att köra hela pipelinen:

```bash
python setup_project.py
```

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

🧰 Ytterligare standardbibliotek som används: argparse, csv, logging, pathlib, json, re, os, asyncio, typing

Installera alla beroenden med:

```bash
pip install -r requirements.txt
```

## Byta till en annan LLM

Jag har tagit fram en kort guide för _ungefär_ vad som behöver bytas ut för att använda en annan LLM, se [BYTA_LLM.md](./BYTA_LLM.md).

## 🪪 Licens

Detta projekt är licensierat under MIT-licensen, med ett tilläggskrav:

> Om du återanvänder **VÄSENTLIGA DELAR AV KODEN ELLER DESS STRUKTUR** i en kommersiell produkt eller i en offentligt distribuerad eller publicerad tjänst, måste du ge tydlig attribution såsom:  
> _"Baserat på arbete av Carl O. Mattsson / Roadlake Analytics AB"_

- I praktiken innebär detta att du inte får påstå att du skrev det i det skick som det återfinns häri.

Se filen [LICENSE](./LICENSE.txt) för fullständiga detaljer.