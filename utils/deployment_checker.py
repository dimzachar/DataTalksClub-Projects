import os
import re
import base64
import logging

import requests

from utils.github_url_constructor import GithubURLConstructor

logging.basicConfig(level=logging.DEBUG, filename='debug.log', filemode='a')

headers = {"Authorization": f"token {os.environ.get('GITHUB_ACCESS_TOKEN')}"}

print(headers)


class DeploymentChecker:
    def __init__(
        self, batch_keywords, web_service_keywords, streaming_keywords, cloud_keywords
    ):
        self.batch_keywords = batch_keywords
        self.web_service_keywords = web_service_keywords
        self.streaming_keywords = streaming_keywords
        self.cloud_keywords = cloud_keywords
        self.url_constructor = GithubURLConstructor()

    def check_keywords(self, content, keywords):
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', content, re.IGNORECASE):
                return keyword
        return None

    def check_cloud_provider(self, content):
        # logging.debug(
        #     f"Checking for cloud provider in content: {content[:100]}..."
        # )
        provider_counts = {}

        for provider, keywords in self.cloud_keywords.items():
            for keyword in keywords:
                if re.search(
                    r'\b' + re.escape(keyword) + r'\b', content, re.IGNORECASE
                ):
                    logging.debug(
                        f"Found cloud provider {provider} for keyword {keyword}"
                    )
                    provider_counts[provider] = provider_counts.get(provider, 0) + 1

        # If multiple providers are found, prioritize based on frequency and order in cloud_keywords
        if provider_counts:
            sorted_providers = sorted(
                provider_counts.keys(),
                key=lambda x: (
                    -provider_counts[x],
                    list(self.cloud_keywords.keys()).index(x),
                ),
            )
            return sorted_providers[0]

        logging.debug("No cloud provider found.")
        return 'Unknown'

    def fetch_readme_via_api(self, project_url):
        (
            api_url_with_main,
            api_url_without_main,
        ) = self.url_constructor.construct_readme_api_url(project_url)

        if api_url_with_main is None and api_url_without_main is None:
            return None

        # Try the first URL
        response = requests.get(api_url_with_main, headers=headers, timeout=20)
        if response.status_code == 200:
            json_data = response.json()
            readme_content = base64.b64decode(json_data['content']).decode('utf-8')
            return readme_content.lower()
        else:
            logging.debug(
                f"Failed to fetch README via API for URL {api_url_with_main}: {response.status_code}"
            )

        # Try the second URL if the first one fails
        response = requests.get(api_url_without_main, headers=headers, timeout=20)
        if response.status_code == 200:
            json_data = response.json()
            readme_content = base64.b64decode(json_data['content']).decode('utf-8')
            return readme_content.lower()
        else:
            logging.debug(
                f"Failed to fetch README via API for URL {api_url_without_main}: {response.status_code}"
            )

        return None

    def check_deployment_type(self, url):
        # use Github API instead of web scrape
        try:
            if url is None:
                logging.debug("Received None URL. Skipping.")
                return 'Unknown', 'Unknown', 'Unknown'

            # Sanitize the URL to remove any fragment
            sanitized_url = self.url_constructor.sanitize_url(url)

            # Now use the sanitized URL to fetch the README
            readme_content = self.fetch_readme_via_api(sanitized_url)
            if readme_content is None:
                logging.debug(f"No README found for URL: {url}")
                return 'Unknown', 'Unknown', 'Unknown'

            # logging.debug(f"Entire Readme content for URL {url}: {readme_content}")

            deployment_keyword = 'Unknown'
            reason_keyword = 'Unknown'

            # Debug logging for cloud keyword search
            logging.debug(f"Checking cloud keywords for URL: {url}")
            # logging.debug(
            #     f"Readme content: {readme_content[:100]}..."
            # )  # First 100 characters of README

            # Check for deployment type
            keyword = self.check_keywords(readme_content, self.batch_keywords)
            if keyword:
                deployment_keyword = 'Batch'
                reason_keyword = keyword
            else:
                keyword = self.check_keywords(readme_content, self.web_service_keywords)
                if keyword:
                    deployment_keyword = 'Web Service'
                    reason_keyword = keyword
                else:
                    keyword = self.check_keywords(
                        readme_content, self.streaming_keywords
                    )
                    if keyword:
                        deployment_keyword = 'Streaming'
                        reason_keyword = keyword

            # Check for cloud tool
            cloud_provider = self.check_cloud_provider(readme_content)

            if cloud_provider == 'Unknown':
                logging.debug(f"No cloud keyword found in README for URL: {url}")
            else:
                logging.debug(
                    f"Found cloud provider {cloud_provider} in README for URL: {url}"
                )

            return deployment_keyword, reason_keyword, cloud_provider

        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking for URL {url}: {e}")
            return 'Error', 'Error', 'Error'
