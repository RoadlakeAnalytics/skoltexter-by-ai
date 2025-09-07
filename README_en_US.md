# 📊 School Description Data Pipeline

> 1 Minute Demo
>
> - Pipeline demo: shows launching `setup_project.py`, the guided menu flow, venv management, running steps 1–3, and opening `output/index.html` with the search field.
>
>   ![Pipeline Demo](assets/sub1min_pipeline_run.gif)

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
- [🧪 Testing](#testing)
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

### 🏷️ CI/Badges

[![codecov](https://codecov.io/gh/RoadlakeAnalytics/skoltexter-by-ai/badge.svg)](https://codecov.io/gh/RoadlakeAnalytics/skoltexter-by-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![ruff](https://img.shields.io/badge/lint-ruff-informational)
![mypy --strict](https://img.shields.io/badge/types-mypy%20--strict-informational)
![Bandit](https://img.shields.io/badge/security-bandit-informational)
![pip-audit](https://img.shields.io/badge/deps-pip--audit-informational)

- **📃 Configuration & Environment**
  - `.env-example`: Template for required Azure OpenAI environment variables.
  - `.gitignore`: Excludes sensitive data, build artifacts, and generated outputs.

## 📁 Project Structure

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

Note: During execution, additional result folders and files are created, including:
- `data/generated_markdown_from_csv/` (markdown generated from CSV)
- `data/ai_processed_markdown/` (AI‑enhanced markdown)
- `data/ai_raw_responses/` (raw AI responses and failures)
- `output/index.html` (generated website)
- `logs/` (runtime logs)

The `tests/` folder contains a test suite of 128 tests (100% coverage) which is run with `pytest`.

## ⚙️ Prerequisites

- 🐍 Python 3.11+
- 🔑 Azure OpenAI API access (GPT-4o deployment)
- 📈 School statistics CSV in the expected format (included)
- 🌐 Internet connection

## 🚀 Setup

### ✅ Recommended: Interactive Setup

Run the interactive setup script and follow the menu prompts (supports English/Swedish):

```bash
python setup_project.py
```

Once dependencies (e.g., `rich` and `questionary`) are installed, the setup
program automatically restarts inside the virtual environment to enable the
enhanced UI without extra steps.

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

When starting the pipeline, you will first be prompted to run a quick AI connectivity test. It sends a minimal request to verify that your `.env` and network configuration are working. If it passes, the pipeline continues; otherwise, you get a clear error message so you can fix issues before re‑running.

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

## 🧪 Testing

- Run full test suite (quiet):

  ```bash
  pytest -q
  ```

- Run with coverage and show missing lines:

  ```bash
  pytest --cov=src --cov=setup_project --cov-report=term-missing --cov-report=xml
  ```

- Coverage gate in CI: 100%.
- Type checking and lint run in CI. Locally:

  ```bash
  ruff check .
  mypy --strict src setup_project.py
  ```

- Pre-commit (format, lint, security checks):

  ```bash
  pip install -r requirements.txt
  pre-commit install
  pre-commit run --all-files
  ```

## Switching to a different LLM

I have provided a brief file regarding configuration options for other LLM models, see `BYTA_LLM.md`

## 🪪 License

This project is licensed under the MIT License.

See the [LICENSE](./LICENSE) file for full details.

## 🔐 Security & Reliability

- Lint & Types: `ruff` (no warnings) and `mypy --strict` in CI.
- Security scanning: `bandit` (MEDIUM+), `pip-audit` for CVEs, and secret scanning via Gitleaks.
- SBOM: Generated with CycloneDX in CI (`sbom.json`).
- Tests: `pytest` with coverage gating in CI; async tests with network fakes; timeouts/backoff in runtime code.
- Rate limiting & retries: All AI calls use limiter + exponential backoff; request timeouts via `aiohttp.ClientTimeout`.
- Logging hygiene: No API keys or PII in logs. File logging is disabled in tests.
 - Reproducibility: All tooling is listed in `requirements.txt`. Pre-commit hooks enforce style and common security checks locally.

License allowlist

- Allowed: MIT, BSD-2/3-Clause, Apache-2.0, ISC, MPL-2.0, PSF/Python, and similar permissive licenses.
- Enforced via a pre-commit hook (`pip-licenses`) and in CI; see `tools/policy/check_licenses.py`.

Local pre-commit setup:

```bash
pip install -r requirements.txt
pre-commit install
pre-commit run --all-files
```
