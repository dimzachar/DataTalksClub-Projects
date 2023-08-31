test:
	pytest tests/

quality_checks:
	isort .
	black .
	pylint --recursive=y .

scrape: quality_checks
	python -m src.scrape_and_clean

titles:
	python -m src.generate_and_save_titles

deploy:
	python -m src.check_and_save_deployment

all: scrape titles deploy
