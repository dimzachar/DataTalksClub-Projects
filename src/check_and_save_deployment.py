import os
import logging

from utils.csv_handler import CSVHandler
from utils.deployment_checker import DeploymentChecker
from utils.github_url_constructor import GithubURLConstructor

from .config import get_config


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Get the configuration
    config = get_config()

    # Initialize CSVHandler
    csv_handler = CSVHandler(config['titles_csv_path'])
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
            'S3',
            'CloudFront',
            'Route 53',
            'IAM',
            'VPC',
            'ELB',
            'Kinesis',
            'SNS',
            'SQS',
            'CloudFormation',
            'CloudWatch',
            'Redshift',
            'EKS',
            'ECS',
            'Fargate',
            'SageMaker',
            'Athena',
            'EMR',
            'CloudTrail',
            'AWS Glue',
            'AWS Step Functions',
            'AWS Batch',
            'Amazon OpenSearch Service',  
        ],
        'GCP': [
            'GCP',
            'Google Cloud',
            'Google Cloud Platform',
            'Google Cloud Storage',
            'GCS',
            'BigQuery',
            'Compute Engine',
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
            'Vertex AI',
            'Dataproc',
        ],
        'Azure': [
            'Azure',
            'Azure VM',
            'Azure Functions',
            'Azure Cosmos DB',
            'Azure SQL Database',
            'Azure Blob Storage',
            'Azure Data Lake',
            'Azure Kubernetes Service',
            'Azure Container Instances',
            'Azure Active Directory',
            'Azure DevOps',
            'Azure Monitor',
            'Azure Logic Apps',
            'Azure Service Bus',
            'Azure Event Grid',
            'Azure Cognitive Services',
            'Azure Machine Learning',
        ],
        'IBM Cloud': [
            'IBM Cloud',
            'IBM Cloud Functions',
            'IBM Cloud Object Storage',
            'IBM Db2',
            'IBM Watson',
            'IBM Kubernetes Service',
        ],
        'Oracle Cloud': [
            'Oracle Cloud',
            'Oracle Cloud Infrastructure',
            'OCI',
            'Oracle Autonomous Database',
            'Oracle Container Engine for Kubernetes',
        ],
        'Alibaba Cloud': [
            'Alibaba Cloud',
            'Aliyun',
            'Alibaba ECS',
            'Alibaba OSS',
            'Alibaba RDS',
            'Alibaba Cloud Container Service',
        ],
        'DigitalOcean': [
            'DigitalOcean',
            'DigitalOcean Droplets',
            'DigitalOcean Spaces',
            'DigitalOcean Kubernetes',
        ],
        'Heroku': ['Heroku', 'Heroku Dynos', 'Heroku Postgres'],
        'Linode': ['Linode', 'Linode Kubernetes Engine', 'Linode Object Storage'],
        'Vultr': ['Vultr', 'Vultr Cloud Compute', 'Vultr Block Storage'],
        'Hetzner Cloud': ['Hetzner Cloud', 'Hetzner'],
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
    }

    checker = DeploymentChecker(
        batch_keywords, web_service_keywords, streaming_keywords, cloud_keywords
    )

    # Check deployment type and update DataFrame
    def check_deployment(url):
        try:
            return checker.check_deployment_type(url)
        except Exception as e:
            logger.error(f"Error checking deployment for URL {url}: {str(e)}")
            return 'Unknown', 'Error', 'Unknown'

    results = csv_handler.df['project_url'].apply(check_deployment)

    (
        csv_handler.df['Deployment Type'],
        csv_handler.df['Reason'],
        csv_handler.df['Cloud'],
    ) = zip(*results)

    # Log URLs with unknown clouds
    unknown_clouds = csv_handler.df[csv_handler.df['Cloud'] == 'Unknown']
    logger.info("URLs with unknown cloud:")
    for url in unknown_clouds['project_url']:
        logger.info(url)

    csv_handler.save(config['deploy_csv_path'])
    logger.info("Deployment type checking and final CSV saving completed.")

    unknown_count = csv_handler.df['Cloud'].value_counts().get('Unknown', 0)
    total_count = len(csv_handler.df)
    logger.info(
        f"Number of unknown clouds: {unknown_count} out of {total_count} total projects"
    )
    logger.info(
        f"Percentage of unknown clouds: {(unknown_count / total_count) * 100:.2f}%"
    )


if __name__ == "__main__":
    main()
