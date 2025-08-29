# 📊 School Description Data Pipeline

This project is a data processing pipeline that transforms raw Swedish school statistics (CSV) into AI-enhanced descriptions and generates a modern, interactive website for browsing school information. The primary goal is to make complex school data accessible and useful for parents choosing schools, while also serving as a robust foundation for advanced AI text generation use cases.

## 🗂️ Table of Contents

- [🔍 Overview](#overview)
- [🧩 Main Components](#main-components)
- [📁 Project Structure](#project-structure)
- [⚙️ Prerequisites](#prerequisites)
- [🚀 Setup](#setup)
- [▶️ Usage](#usage)
- [🔧 Operational Details](#operational-details)
- [📝 Logging](#logging)
- [📦 Dependencies](#dependencies)
- [🤖 Switching to a different LLM](#switching-to-a-different)
- [🪪 License](#license)

## 🔍 Overview

This pipeline processes Swedish school statistics through three main stages:

1. 📝 **CSV to Markdown**: Reads raw CSV data and generates a markdown file per school using a template.
2. 🤖 **AI Enhancement**: Processes each markdown file with Azure OpenAI (GPT-4o) to generate enhanced, parent-focused descriptions.
3. 🌐 **Website Generation**: Loads school codes/names and AI-generated descriptions, converts markdown to HTML, and generates a standalone, interactive HTML website.

---

### 🚀 Raw data to website in less than 5 minutes 🚀

If you already have an Azure OpenAI endpoint and have your three values for key, endpoint and model name within reach, you can comfortably expect to run the whole pipeline within the next five minutes, using the guided `setup_project.py` program, which guides your through the process:
- Configuring the program with the correct values (optional, can be done manually).
- Creating a virtual environment for Python (optional - takes 2-3 minutes, but recommended).
- Taking the time to read short summaries for the programs (optional).
- Running the pipeline:
  - Step one creates the 44 Markdown files.
  - Step two sends them to the AI and saves the responses.
  - Step three creates a small website for you to easily browse the data (optional).
- Now you need to open the generated `index.html` file inside of the folder `output` (manually clicking it, which opens the web browser - optional but recommended).
- Read a school description (if not using a browser you will find them in the folder `data/ai_processed_markdown/`).

> If you skip the virtual environment, and have the .env file set up, you will be able to run the whole pipeline in less than 1 minute. 🚀

## 🧩 Main Components

- **📊 Data & Templates**
  - `data/database_data/database_school_data.csv`: Main input CSV with school statistics, identifiers, and survey results.
  - `data/templates/school_description_template.md`: Markdown template for per-school reports.
  - `data/templates/ai_prompt_template.txt`: Prompt template for Azure OpenAI, specifying requirements for the AI-generated descriptions.
  - `data/templates/website_template.html`: Responsive HTML template for the generated website.

- **🧠 Source Code (`src/`)**
  - [`src/config.py`](src/config.py): Centralizes all constants, paths, and configuration.
  - [`src/program1_generate_markdowns.py`](src/program1_generate_markdowns.py): Generates markdown files from the CSV.
  - [`src/program2_ai_processor.py`](src/program2_ai_processor.py): Processes markdown files with Azure OpenAI, handling rate limiting and retries.
  - [`src/program3_generate_website.py`](src/program3_generate_website.py): Generates the interactive HTML website.

- **🛠️ Orchestration & Setup**
  - `setup_project.py`: Interactive, menu-driven CLI for managing the pipeline, supporting language selection, environment management, dependency installation, pipeline execution, log viewing, and file resets.

- **📃 Configuration & Environment**
  - `.env-example`: Template for required Azure OpenAI environment variables.
  - `.gitignore`: Excludes sensitive data, build artifacts, and generated outputs.

## 📁 Project Structure

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

## ⚙️ Prerequisites

- 🐍 Python 3.7+
- 🔑 Azure OpenAI API access (GPT-4o deployment)
- 📈 School statistics CSV in the expected format
- 🌐 Internet connection

## 🚀 Setup

### ✅ Recommended: Interactive Setup

Run the interactive setup script and follow the menu prompts (supports English/Swedish):

```bash
python setup_project.py
```

### 🔧 Manual Setup
1. Copy `.env-example` to `.env` and fill in Azure credentials.
2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
3. Place your CSV at `data/database_data/database_school_data.csv`.

Ensure the CSV file follows the expected format with columns for school statistics, identifiers, and survey results.

## ▶️ Usage

### 🧭 Interactive

Use the setup script's menu to run the full pipeline:

```bash
python setup_project.py
```

### 🛠️ Manual

Generate markdown:

```bash
python src/program1_generate_markdowns.py
```

AI process markdown:

```bash
python src/program2_ai_processor.py
```

Generate website:

```bash
python src/program3_generate_website.py
```

## 🔧 Operational Details

- **Input**: `data/database_data/database_school_data.csv` (school statistics)
- **Templates**: `data/templates/` (markdown, AI prompt, website)
- **AI-enhanced markdown output**: `data/ai_processed_markdown/`
- **Raw/failed AI responses**: `data/ai_raw_responses/`
- **Website output**: `output/index.html`
- **Logs**: `logs/` (all major steps log detailed info)

## 📝 Logging

All major steps log to the `logs/` directory with detailed information for troubleshooting and performance monitoring.

| 📄 Log File                | 🧾 Description                     |
|----------------------------|-----------------------------------|
| `generate_markdowns.log`   | CSV processing                    |
| `ai_processor.log`         | AI service communication           |
| `generate_website.log`     | Website generation                 |

## 📦 Dependencies

From `requirements.txt`:

- pandas
- openpyxl
- aiohttp
- aiolimiter
- python-dotenv
- tqdm
- Jinja2
- markdown2

🧰 Additional standard library modules used: argparse, csv, logging, pathlib, json, re, os, asyncio, typing

Install all dependencies with:

```bash
pip install -r requirements.txt
```

## Switching to a different LLM

I have provided a brief file regarding configuration options for other LLM models, see `BYTA_LLM.md`

## 🪪 License

This project is licensed under the MIT License, with an added requirement:

> If you reuse **SUBSTANTIAL PORTIONS OF THE CODE OR ITS STRUCTURE** in a commercial product or in a publicly deployed or published service, you must provide clear attribution such as: 
> _"Based on work by Carl O. Mattsson / Roadlake Analytics AB"_

- Essentially, you can not claim you wrote the program as is.

See the [LICENSE](./LICENSE.txt) file for full details.
