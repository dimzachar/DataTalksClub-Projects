import os

from utils.csv_handler import CSVHandler
from utils.deployment_checker import DeploymentChecker
from utils.github_url_constructor import GithubURLConstructor

from .config import deploy_csv_path, titles_csv_path


def main():
    # Initialize CSVHandler
    csv_handler = CSVHandler(titles_csv_path)
    url_constructor = GithubURLConstructor()
    # Define keywords for deployment types
    batch_keywords = ['batch', 'hadoop', 'spark']
    web_service_keywords = [
        'flask',
        'django',
        'fastapi',
        'web service',
        'gunicorn',
        'bentoml',
    ]
    streaming_keywords = ['stream', 'real-time', 'kafka', 'streaming', 'kinesis']
    # Define keywords for cloud providers
    cloud_keywords = {
        'AWS': [
            'AWS',
            'Amazon Web Services',
            'EC2',
            'Lambda',
            'DynamoDB',
            'RDS',
            'Elastic Beanstalk',
            'Kinesis',
            'SNS',
            'SQS',
            'CloudFormation',
            'CloudWatch',
            'Elasticsearch',
            'Redshift',
            'EKS',
            'ECS',
            'SageMaker',
            'Athena',
            'EMR',
            'Fargate',
        ],
        'GCP': [
            'GCP',
            'Google Cloud',
            'Google Cloud Platform',
            'Google Cloud Storage',
            'gcs',
            'GCS',
            'BigQuery',
            'Google Compute Engine',
            'GKE',
            'Cloud Functions',
            'Cloud Run',
            'Datastore',
            'Cloud Spanner',
            'Cloud SQL',
            'Cloud Dataflow',
            'Cloud Dataprep',
            'Cloud Endpoints',
            'Cloud Natural Language',
            'Cloud Vision',
            'Cloud Speech-to-Text',
            'Cloud Text-to-Speech',
            'Cloud Translation',
            'Cloud Talent Solution',
            'Cloud Armor',
            'Cloud CDN',
            'Cloud DNS',
            'Cloud Load Balancing',
            'Cloud VPN',
            'Cloud Interconnect',
            'Cloud Router',
        ],
        'Yandex Cloud': [
            'Yandex Cloud',
            'Yandex Object Storage',
            'Yandex Managed Service for Kubernetes',
            'Yandex Managed Service for PostgreSQL',
            'Yandex Managed Service for MySQL',
            'Yandex Managed Service for ClickHouse',
            'Yandex Compute Cloud',
            'Yandex Datalens',
            'Yandex Data Proc',
            'Yandex DataSphere',
            'Yandex Cloud Functions',
            'Yandex Message Queue',
            'Yandex API Gateway',
            'Yandex Cloud Monitoring',
            'Yandex Cloud Logging',
            'Yandex Cloud Audit',
        ],
        'Azure': ['Azure'],
        'Hetzner Cloud': ['Hetzner Cloud', 'Hetzner'],
    }

    checker = DeploymentChecker(
        batch_keywords, web_service_keywords, streaming_keywords, cloud_keywords
    )

    # Check deployment type and update DataFrame
    (
        csv_handler.df['Deployment Type'],
        csv_handler.df['Reason'],
        csv_handler.df['Cloud'],
    ) = zip(*csv_handler.df['project_url'].apply(checker.check_deployment_type))

    csv_handler.save(deploy_csv_path)
    print("Deployment type checking and final CSV saving completed.")


if __name__ == "__main__":
    main()
