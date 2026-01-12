# DataTalksClub-Projects

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://datatalksclub-projects.streamlit.app/)

https://github.com/dimzachar/DataTalksClub-Projects/assets/113017737/c3c3235c-951c-47e8-aa6a-a6dffa159e46

## Table of Contents

- [Introduction](#introduction)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [View the Dashboard](#view-the-dashboard)
- [Run the Data Pipeline](#run-the-data-pipeline)
- [Testing](#testing)
- [Quality Checks](#quality-checks)
- [Local Development](#local-development-without-docker)
- [Output Data](#output-data)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Introduction

DataTalksClub-Projects automates the analysis of projects from [DataTalksClub](https://github.com/DataTalksClub) courses. It scrapes project submissions, generates descriptive titles using LLMs, and classifies deployment types (Batch/Streaming) and cloud providers (GCP/AWS/Azure).

**Supported courses:**
- [DE Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp) (dezoomcamp) → Batch, Streaming
- [ML Zoomcamp](https://github.com/DataTalksClub/machine-learning-zoomcamp) (mlzoomcamp) → Batch, Web Service
- [MLOps Zoomcamp](https://github.com/DataTalksClub/mlops-zoomcamp) (mlopszoomcamp) → Batch, Web Service
- [LLM Zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp) (llmzoomcamp) → Batch, Web Service

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DataTalksClub Website                              │
│                    courses.datatalks.club/*/projects                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         1. SCRAPE & DISCOVER                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ Course Discovery │───▶│  Web Scraping   │───▶│  CSV Generation │          │
│  │ (Auto-detect new │    │ (BeautifulSoup) │    │ (project URLs)  │          │
│  │  finished courses)│    └─────────────────┘    └─────────────────┘          │
│  └─────────────────┘                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         2. MULTI-FILE FETCHING                               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │   GitHub API    │───▶│  Repo Analyzer  │───▶│  Key Files:     │          │
│  │  (Tree + Files) │    │ (Prioritization)│    │  • README.md    │          │
│  └─────────────────┘    └─────────────────┘    │  • docker-compose│          │
│                                                 │  • *.tf (Terraform)│        │
│         Parallel fetching with ThreadPool       │  • requirements.txt│        │
│         (5 workers default, configurable)       │  • Dockerfile    │          │
│                                                 │  • dags/*.py     │          │
│                                                 └─────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      3. LLM CLASSIFICATION & TITLE GEN                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │  OpenRouter API │───▶│ Classification  │───▶│ Title Generation│          │
│  │ (Free LLM tier) │    │ • Deployment    │    │ (Domain-focused,│          │
│  └─────────────────┘    │   Type          │    │  tech-accurate) │          │
│                         │ • Cloud Provider│    └─────────────────┘          │
│                         └─────────────────┘                                  │
│                                                                              │
│  Classification runs FIRST → Title uses deployment context                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            4. OUTPUT                                         │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │  Data/{course}/{year}/data.csv                               │            │
│  │  ├── project_url                                             │            │
│  │  ├── project_title    (LLM-generated, domain-specific)       │            │
│  │  ├── Deployment Type  (Batch, Streaming, Web Service)        │            │
│  │  ├── Reason           (Evidence from code files)             │            │
│  │  └── Cloud            (GCP, AWS, Azure, Other, Unknown)      │            │
│  └─────────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## How It Works

### Pipeline Steps

1. **Course Discovery** - Automatically detects finished courses from DataTalksClub website
2. **Web Scraping** - Extracts project submission URLs from course pages
3. **Multi-File Fetching** - For each GitHub repo, fetches 10 key files (not just README):
   - `docker-compose.yml` → Shows Kafka, Spark, orchestrators
   - `*.tf` files → Definitive cloud provider indicator
   - `dags/*.py` → Airflow = Batch
   - `requirements.txt` → Dependencies
   - `Dockerfile`, `Makefile`, etc.
4. **LLM Classification** - Analyzes actual code to determine:
   - **Deployment Type**: Batch (Airflow, Kestra, Mage) or Streaming (Kafka, Flink)
   - **Cloud Provider**: GCP, AWS, Azure based on Terraform/SDK usage
5. **Title Generation** - Creates descriptive titles based on:
   - Actual project functionality (not repo name)
   - Deployment type context (no "Real-Time" for Batch projects)
   - Domain focus (e.g., "NYC Taxi Analytics Pipeline")

### Key Features

- **Parallel Processing**: 5-10x faster with configurable workers
- **Smart Skipping**: Only processes new courses by default
- **Multi-File Context**: Better accuracy than README-only analysis
- **Course-Specific Types**: Each course has valid deployment types
- **Nested Project Support**: Handles `/tree/main/project` URLs correctly

### Performance

| Metric | Before (Sequential) | After (Parallel, 5 workers) |
|--------|--------------------|-----------------------------|
| 381 projects | ~60 minutes | ~12-15 minutes |
| Throughput | ~0.1 proj/sec | ~0.5 proj/sec |

## Getting Started

### Prerequisites

- Docker and Docker Compose
- GitHub Personal Access Token ([create one](https://github.com/settings/tokens)) - for pipeline
- OpenRouter API Key ([get free tier](https://openrouter.ai/)) - for pipeline

### Setup

```bash
git clone https://github.com/dimzachar/DataTalksClub-Projects.git
cd DataTalksClub-Projects

# For pipeline: copy and edit .env
cp .env.example .env

# Build Docker image
make docker-build
```

---

## View the Dashboard

The easiest way - just visit the live app: **[datatalksclub-projects.streamlit.app](https://datatalksclub-projects.streamlit.app/)**

Or run locally with Docker:

| Make Command | Direct Docker Command |
|--------------|----------------------|
| `docker-compose up streamlit` | Same |

Then open http://localhost:8501

---

## Run the Data Pipeline

### Docker Commands (Recommended)

| Make Command | Direct Docker Command | Description |
|--------------|----------------------|-------------|
| `make docker-build` | `docker-compose build` | Build Docker image (run once) |
| `make docker-discover` | `docker-compose run --rm pipeline python -m src.pipeline_runner --discover` | See available courses |
| `make docker-pipeline` | `docker-compose run --rm pipeline python -m src.pipeline_runner` | Process new courses only |
| `make docker-pipeline-all` | `docker-compose run --rm pipeline python -m src.pipeline_runner --all` | Reprocess all courses |
| `make docker-pipeline-single COURSE=dezoomcamp YEAR=2025` | `docker-compose run --rm pipeline python -m src.pipeline_runner --course dezoomcamp --year 2025` | Process specific course |
| `make docker-pipeline-test COURSE=dezoomcamp YEAR=2025 LIMIT=10` | `docker-compose run --rm pipeline python -m src.pipeline_runner --course dezoomcamp --year 2025 --limit 10` | Test with limited projects |

### Pipeline Options

| Option | Description |
|--------|-------------|
| `--discover` | List available courses and their status |
| `--all` | Reprocess all courses (overwrites existing) |
| `--course NAME` | Process specific course |
| `--year YEAR` | Process specific year |
| `--limit N` | Limit to N projects (for testing) |
| `--workers N` | Parallel workers (default: 5) |

---

## Testing

| Make Command | Direct Docker Command | Description |
|--------------|----------------------|-------------|
| `make docker-test` | `docker-compose run --rm pipeline python -m pytest tests/ -v` | Run all tests in Docker |
| `make docker-test-cov` | `docker-compose run --rm pipeline python -m pytest tests/ -v --cov=...` | Run tests with coverage in Docker |
| `make test` | `python -m pytest tests/ -v` | Run all tests locally |
| `make test-cov` | `python -m pytest tests/ -v --cov=...` | Run tests with coverage locally |
| `make test-unit` | - | Run unit tests only |
| `make test-e2e` | - | Run E2E/integration tests only |

---

## Quality Checks

| Make Command | Direct Docker Command | Description |
|--------------|----------------------|-------------|
| `make quality_checks` | - | Run isort, black, pylint locally |
| `make docker-quality-checks` | `docker-compose run --rm pipeline python -m isort . && ...` | Run isort, black, pylint in Docker |

---

## Local Development (without Docker)

> Requires Python 3.11. Python 3.12+ has dependency issues.

### Setup with uv

```bash
uv venv --python 3.11
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac
uv pip install -r requirements.txt
```

### Setup with pip

```bash
python3.11 -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### Local Commands

| Make Command | Description |
|--------------|-------------|
| `make streamlit` | Run Streamlit dashboard |
| `make pipeline` | Process new courses |
| `make pipeline-all` | Reprocess all courses |
| `make pipeline-discover` | Show available courses |
| `make pipeline-single COURSE=dezoomcamp YEAR=2025` | Process single course |

## Output Data

Generated data is saved to `Data/{course}/{year}/data.csv`:

| Column | Description | Example |
|--------|-------------|---------|
| `project_url` | GitHub repository URL | `https://github.com/user/repo` |
| `project_title` | LLM-generated title | `NYC Taxi Fare Analytics Pipeline` |
| `Deployment Type` | Pipeline type | `Batch`, `Streaming`, `Batch, Streaming` |
| `Reason` | Classification evidence | `Found Airflow DAG in dags/pipeline.py` |
| `Cloud` | Cloud provider | `GCP`, `AWS`, `Azure`, `Other`, `Unknown` |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests: `make docker-test`
5. Run `make quality_checks`
6. Submit a pull request

### CI/CD

- **Tests**: Run automatically on every PR and push to main
- **Pipeline**: Runs quarterly (Jan, Apr, Jul, Oct) to update course data
- **Coverage**: Minimum 80% required for pipeline files

## License

MIT License - see `LICENSE` file.

## Contact

Connect on [LinkedIn](https://www.linkedin.com/in/zacharenakis/)

## Support this project

[![Donate with PayPal](https://www.paypalobjects.com/digitalassets/c/website/marketing/apac/C2/logos-buttons/optimize/26_Yellow_PayPal_Pill_Button.png)](https://www.paypal.com/donate/?hosted_button_id=LR3PQYHZY4CJ4)
