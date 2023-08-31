import os

from utils.csv_handler import CSVHandler
from utils.deployment_checker import DeploymentChecker

from .config import deploy_csv_path, titles_csv_path


def main():
    # Initialize CSVHandler
    csv_handler = CSVHandler(titles_csv_path)

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
