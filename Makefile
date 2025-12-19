# Variables
COURSE ?= dezoomcamp
YEAR ?= 2024
BASE_PATH ?= Data

# Common arguments for Python scripts
PY_ARGS = --course $(COURSE) --year $(YEAR) --base_path $(BASE_PATH)

# =============================================================================
# TESTING
# =============================================================================

# Run all tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --cov=utils --cov=src --cov-report=term-missing

# Run tests with coverage (pipeline files only)
test-cov-pipeline:
	python -m pytest tests/ -v --cov=src.config --cov=src.combine_csvs --cov=src.generate_titles_and_classify --cov=src.pipeline_runner --cov=utils.csv_handler --cov=utils.course_discovery --cov=utils.scraping_handler --cov=utils.repo_analyzer --cov=utils.openai_api --cov-report=term-missing

# Run only unit tests
test-unit:
	python -m pytest tests/test_config.py tests/test_csv_handler.py tests/test_csv_handler_mojibake.py tests/test_combine_csvs.py tests/test_scraping_handler.py tests/test_course_discovery.py tests/test_repo_analyzer.py tests/test_openai_api.py tests/test_generate_titles_and_classify.py tests/test_pipeline_runner.py tests/test_mojibake.py tests/test_df_thread_safety.py tests/test_app_year_discovery.py tests/test_edge_cases.py -v

# Run only e2e/integration tests
test-e2e:
	python -m pytest tests/test_e2e.py tests/test_pipeline_e2e.py tests/test_integration.py -v

# Run tests in Docker
docker-test:
	docker-compose run --rm pipeline python -m pytest tests/ -v

# Run tests in Docker with coverage
docker-test-cov:
	docker-compose run --rm pipeline python -m pytest tests/ -v --cov=src.config --cov=src.combine_csvs --cov=src.generate_titles_and_classify --cov=src.pipeline_runner --cov=utils.csv_handler --cov=utils.course_discovery --cov=utils.scraping_handler --cov=utils.repo_analyzer --cov=utils.openai_api --cov-report=term-missing

# Run quality checks (isort, black, pylint) in Docker
docker-quality-checks:
	docker-compose run --rm pipeline python -m isort .
	docker-compose run --rm pipeline python -m black .
	docker-compose run --rm pipeline python -m pylint --recursive=y .

# =============================================================================
# DOCKER PIPELINE (no local install needed)
# =============================================================================

# Build Docker image (run once)
docker-build:
	docker-compose build

# Show available courses (no API keys needed)
docker-discover:
	docker-compose run --rm pipeline python -m src.pipeline_runner --discover

# Process only new/missing courses
docker-pipeline:
	docker-compose run --rm pipeline python -m src.pipeline_runner

# Force reprocess ALL courses
docker-pipeline-all:
	docker-compose run --rm pipeline python -m src.pipeline_runner --all

# Process a single specific course
docker-pipeline-single:
	docker-compose run --rm pipeline python -m src.pipeline_runner --course $(COURSE) --year $(YEAR)

# Test pipeline with limited projects (default 5)
LIMIT ?= 5
docker-pipeline-test:
	docker-compose run --rm pipeline python -m src.pipeline_runner --course $(COURSE) --year $(YEAR) --limit $(LIMIT)

# Run Streamlit dashboard in Docker
docker-streamlit:
	docker-compose run --rm -p 8501:8501 pipeline streamlit run app.py --server.address 0.0.0.0

# =============================================================================
# LOCAL PIPELINE (requires pip install -r requirements.txt)
# =============================================================================

# Process only new/missing courses (ONE CLICK)
pipeline:
	python -m src.pipeline_runner

# Force reprocess ALL courses (use sparingly - costs API credits)
pipeline-all:
	python -m src.pipeline_runner --all

# Show available courses and what we have
pipeline-discover:
	python -m src.pipeline_runner --discover

# Process a single specific course
pipeline-single:
	python -m src.pipeline_runner --course $(COURSE) --year $(YEAR)

# =============================================================================
# LEGACY COMMANDS (manual step-by-step)
# =============================================================================

combine:
	python -m src.combine_csvs $(PY_ARGS)

quality_checks:
	python -m isort .
	python -m black .
	python -m pylint --recursive=y .

scrape:
	python -m src.scrape_and_clean $(PY_ARGS)

# NEW: Unified title generation + deployment/cloud classification
classify:
	python -m src.generate_titles_and_classify $(PY_ARGS)

# OLD: Separate title generation (README only) - kept for reference
titles-old:
	python -m src.generate_and_save_titles $(PY_ARGS)

# OLD: Separate deployment check (keyword matching) - kept for reference
deploy-old:
	python -m src.check_and_save_deployment $(PY_ARGS)

streamlit:
	streamlit run app.py

all: scrape combine classify