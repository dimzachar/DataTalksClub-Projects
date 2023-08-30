import os

from utils.csv_handler import CSVHandler
from utils.deployment_checker import DeploymentChecker


def main():
    deploy_csv_path = os.path.join("Data", "scraped", "final_output.csv")
    csv_handler = CSVHandler(deploy_csv_path)

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
