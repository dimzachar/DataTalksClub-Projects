# Variables
COURSE ?= dezoomcamp
YEAR ?= 2024
BASE_PATH ?= Data

# Common arguments for Python scripts
PY_ARGS = --course $(COURSE) --year $(YEAR) --base_path $(BASE_PATH)

combine:
	python -m src.combine_csvs $(PY_ARGS)

test:
	python -m pytest tests/

quality_checks:
	isort .
	black .
	pylint --recursive=y .

scrape:
	python -m src.scrape_and_clean $(PY_ARGS)

titles:
	python -m src.generate_and_save_titles $(PY_ARGS)

deploy:
	python -m src.check_and_save_deployment $(PY_ARGS)

streamlit:
	streamlit run app.py

all: scrape titles deploy