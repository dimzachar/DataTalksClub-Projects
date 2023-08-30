test:
	pytest tests/

quality_checks:
	isort .
	black .
	pylint --recursive=y .

scrape:
	python src/perform_data_scraping.py

clean:
	python src/clean_and_save_csv.py

titles: clean
	python src/generate_and_save_titles.py

deploy: titles
	python src/check_and_save_deployment.py

all: test quality_checks data clean titles deploy
