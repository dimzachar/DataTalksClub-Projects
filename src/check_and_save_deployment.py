import os

from utils.csv_handler import CSVHandler
from utils.deployment_checker import DeploymentChecker

# from .config import year, course, base_path
from .config import deploy_csv_path, titles_csv_path


def main():
    # output_prefix = "projects_mlzoomcamp_2021"
    # deploy_csv_path = f"{base_path}/{output_prefix}_cleaned_titles_deploy.csv"

    # The input CSV for this script would be the output from the title generation step
    # input_csv_path = f"{base_path}/{output_prefix}_cleaned_titles.csv"

    # Initialize CSVHandler
    csv_handler = CSVHandler(titles_csv_path)
    # Initialize cleaned_csv_path dynamically (from config or wherever you get it)
    # cleaned_csv_path = os.path.join(base_path, f"cleaned_scraped_{course}_{year}.csv")

    # Initialize csv_handler with the cleaned_csv_path
    # csv_handler = CSVHandler(cleaned_csv_path)

    # Define keywords for deployment types
    batch_keywords = ['batch', 'hadoop', 'spark']
    web_service_keywords = ['flask', 'django', 'fastapi', 'web service', 'gunicorn']
    streaming_keywords = ['stream', 'real-time', 'kafka', 'streaming', 'kinesis']

    # Initialize DeploymentChecker
    checker = DeploymentChecker(
        batch_keywords, web_service_keywords, streaming_keywords
    )

    # Check deployment type and update DataFrame
    csv_handler.df['Deployment Type'], csv_handler.df['Reason'] = zip(
        *csv_handler.df['project_url'].apply(checker.check_deployment_type)
    )

    csv_handler.save(deploy_csv_path)
    print("Deployment type checking and final CSV saving completed.")


if __name__ == "__main__":
    main()
