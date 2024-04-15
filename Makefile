test:
	pipenv run pytest tests/

quality_checks:
	pipenv run isort .
	pipenv run black .
	pipenv run pylint --recursive=y .

scrape:
	pipenv run python -m src.scrape_and_clean

titles:
	pipenv run python -m src.generate_and_save_titles

deploy:
	pipenv run python -m src.check_and_save_deployment

streamlit:
	pipenv run streamlit run app.py

all: scrape titles deploy
