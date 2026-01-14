# 📊 School Description Data Pipeline

> 1 Minute Demo
>
> - Pipeline demo: shows launching `setup_project.py`, the guided menu flow, venv management, running steps 1–3, and opening `output/index.html` with the search field.
>
>   ![Pipeline Demo](assets/sub1min_pipeline_run.gif)

This project is a data processing pipeline that transforms raw Swedish school statistics (CSV) into AI-enhanced descriptions and generates a modern, interactive website for browsing school information. The primary goal is to make complex school data accessible and useful for parents choosing schools, while also serving as a robust foundation for advanced AI text generation use cases.

[![CI](https://github.com/RoadlakeAnalytics/skoltexter-by-ai/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/RoadlakeAnalytics/skoltexter-by-ai/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/RoadlakeAnalytics/skoltexter-by-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/RoadlakeAnalytics/skoltexter-by-ai/branch/main)
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
- [CI Strategy: Local Gating with Remote Verification](#ci-strategy-local-gating-with-remote-verification)
- [🔒 CI/CD: Extreme Strict Mode](#cicd-extreme-strict-mode)
- [🧷 Pre-commit: Local Quality Gates](#pre-commit-local-quality-gates)
- [🤖 Switching to a different LLM](#switching-to-a-different-llm)
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

The `tests/` folder contains a test suite of 143 tests (100% coverage) which is run with `pytest`.

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
# Reproducible & secure (hash-locked) installation
pip install --require-hashes -r requirements.lock

# Alternatively, if you need to update the lock file locally
# (requires pip-tools):
#   pip install pip-tools
#   pip-compile --resolver=backtracking --allow-unsafe \
#     --generate-hashes --no-emit-index-url \
#     -o requirements.lock requirements.txt
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

The main menu also includes quality flows:

- `Q` – Run the full local quality suite (mirrors CI gates).
- `QQ` – Run the EXTREME quality suite: 100 randomized pytest iterations, docstrings 100%, and mutation testing as a gate.

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
- rich
- questionary

🧰 Additional standard library modules used: argparse, csv, logging, pathlib, json, re, os, asyncio, typing

For testing and code control:

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

Install all dependencies with:

```bash
# Prefer hash-locked installation
pip install --require-hashes -r requirements.lock
```

## 🧪 Testing

- Run full test suite (randomized, seed=1):

  ```bash
  pytest -q --randomly-seed=1
  ```

- Run with coverage, branch coverage and 100% gate:

  ```bash
  pytest --randomly-seed=1 \
    --cov=src --cov=setup_project --cov-branch \
    --cov-report=term-missing --cov-report=xml --cov-fail-under=100
  ```

- Also run with a different seed to catch order dependencies:

  ```bash
  pytest -q --maxfail=1 --randomly-seed=2
  ```

- Extreme testing (100 randomized iterations) + mutation testing as a gate:

  ```bash
  python tools/run_all_checks.py --extreme
  ```

- In CI, warnings are treated as errors (see `pytest.ini`).
- Pytest only collects from `tests/` and ignores `mutants/` (mutation-testing artifacts) to keep collection stable.
- Type checking and lint run in CI. Locally:

  ```bash
  ruff check .
  mypy --strict src setup_project.py
  ```

- Pre-commit (format, lint, security checks):

  ```bash
  pip install --require-hashes -r requirements.lock
  pre-commit install
  pre-commit run --all-files
  ```

### CI Strategy: Local Gating with Remote Verification

Our quality strategy is built on the principle of catching errors as early as possible. We use a comprehensive `pre-commit` suite that runs a full local CI/CD pipeline before code can be pushed. GitHub Actions then serves to verify these checks in a clean environment and to run tests that are impractical locally.

1.  Fast Checks (on Pull Request & Push): For every code change, a job runs that exactly mirrors our local `pre-commit` configuration. This verifies linting, typing, security, and tests in a neutral environment, providing feedback within a few minutes.

    - Branch push (pre‑PR): A quick Ubuntu matrix (Python 3.11–3.14) runs with a single pytest seed to provide fast feedback before opening a PR.

2.  Nightly & Weekly Canary Builds:
    - Daily (02:00 UTC): The full test suite is executed against Linux and Windows across all Python versions from 3.11 to 3.14.
    - Weekly (Mondays 03:00 UTC): The same full matrix runs against macOS to ensure cross-platform compatibility while conserving costly CI resources.

    - Purpose: These scheduled jobs are designed to proactively detect issues that emerge over time, such as dependency regressions and platform-specific incompatibilities.

## 🔒 CI/CD: Extreme Strict Mode

This pipeline is locked down and reproducible. Key CI gates (and how to run them locally):

- Reproducible dependencies (hash-locked):
  - CI installs with `pip install --require-hashes -r requirements.lock`.
  - Locally: same command recommended. Regenerate the lock file with pip-tools when `requirements.txt` changes (see setup above).

- Multi-OS test matrix:
  - CI runs tests on `ubuntu`, `windows`, `macos` and Python `3.11–3.14`.

- Pytest in strict mode:
  - All warnings are errors (`pytest.ini: filterwarnings=error`).
  - Tests are run twice in randomized order: seeds `1` and `2`.

- Mutation testing (mutmut):
  - CI fails the build if any mutant survives.
  - Locally: `python tools/ci/mutmut_gate.py` (runs `mutmut` and gates on survivors).
  - CI and pre-commit run a quick cleanup (remove `mutants/` and cache directories) before checks to avoid artifact interference.

- Hardened CI environment:
  - All actions are pinned to commit SHAs.
  - `permissions: contents: read` at top-level; extra rights only per-job when needed.
  - `step-security/harden-runner` blocks unexpected outbound traffic.

- Static analysis and dependency controls:
  - Semgrep runs on PRs using the `p/ci` ruleset and fails on high severity findings.
  - GitHub Dependency Review fails PRs with high severity vulnerabilities.
  - Locally: `pre-commit run semgrep --hook-stage push --all-files`.

- Docstring coverage (interrogate):
  - CI requires 100% docstring coverage.
  - Locally: `interrogate -v --fail-under 100 src/`.

- SBOM (CycloneDX):
  - Generated in CI (from the environment) and uploaded as an artifact. We do not version-control the SBOM file to avoid noise and merge conflicts.
  - Locally: the pre-commit hook performs a non-modifying generation check from `requirements.lock` to a temporary file. No repository diffing is performed.
  - In the `validate-local-checks` job, the SBOM hook is skipped to avoid flaky comparisons; the actual SBOM is published in the `security` job.

Note: We avoid GPL/LGPL in the project's own dependencies. Semgrep is executed via a dedicated pre-commit environment/CI action and does not affect runtime dependencies.

## 🧷 Pre-commit: Local Quality Gates

Install hooks and also enable the pre-push stage so all heavy gates run before pushing:

```bash
pip install --require-hashes -r requirements.lock
pre-commit install
pre-commit install --hook-type pre-push

# Full gates at commit stage (takes longer):
pre-commit run --all-files

# Equivalent full gates at pre-push stage:
pre-commit run --hook-stage pre-push --all-files

# Alternatively, run everything via a single command
python tools/run_all_checks.py

# Extreme mode (100x pytest + mutmut)
python tools/run_all_checks.py --extreme

Note: By default, the virtual environment is created with Python 3.13 when available; otherwise the current interpreter is used. This aligns with our preference for the latest stable Python.
```

## Switching to a different LLM

I have provided a brief file regarding configuration options for other LLM models, see `BYTA_LLM.md`

## 🪪 License

This project is licensed under the MIT License.

See the [LICENSE](./LICENSE) file for full details.

## 🔐 Security & Reliability

- Lint & Types: `ruff` (no warnings) and `mypy --strict` in CI.
- Security scanning: `bandit` (MEDIUM+), `osv-scanner` for CVEs, and secret scanning via Gitleaks.
- SBOM: Generated with CycloneDX in CI (`sbom.json`).
- Tests: `pytest` with coverage gating in CI; async tests with network fakes; timeouts/backoff in runtime code.
- Rate limiting & retries: All AI calls use limiter + exponential backoff; request timeouts via `aiohttp.ClientTimeout`.
- Logging hygiene: No API keys or PII in logs. File logging is disabled in tests.
- Reproducibility: Hash-locked installs from `requirements.lock` using `--require-hashes`. Pre-commit hooks enforce style and security locally.

License allowlist

- Allowed: MIT, BSD‑2/3‑Clause, Apache‑2.0, ISC, MPL‑2.0, PSF/Python, and similar permissive licenses.
- The policy normalizes common license strings (e.g., “MIT License”, “Apache Software License”) to SPDX‑like IDs and supports combinations such as “Apache‑2.0 AND MIT”.
- Known packages with ambiguous or varying license strings are handled through explicit overrides (see the script), and the meta‑package `pre-commit-placeholder-package` is ignored.
- To avoid GPL dependencies, we use the non‑GPL jsonschema extra: `jsonschema[format-nongpl]>=4.18` in `requirements.txt`.
- The allowlist is enforced via pre‑commit and in CI; see `tools/policy/check_licenses.py`.

Local usage:

```bash
pip install -r requirements.txt
pre-commit install
pre-commit run --all-files
# or just the license check
python tools/policy/check_licenses.py
```
