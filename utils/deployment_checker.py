import re

import requests
from bs4 import BeautifulSoup


class DeploymentChecker:
    def __init__(self, batch_keywords, web_service_keywords, streaming_keywords):
        self.batch_keywords = batch_keywords
        self.web_service_keywords = web_service_keywords
        self.streaming_keywords = streaming_keywords

    def check_keywords(self, content, keywords):
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', content, re.IGNORECASE):
                return keyword
        return None

    def check_deployment_type(self, url):
        try:
            # Convert git SSH URL to HTTPS URL if necessary
            if url.startswith('git@'):
                url = url.replace(':', '/')
                url = url.replace('git@', 'https://')
                url = url.replace('.git', '')

            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            readme_element = soup.find(
                'article', {'class': 'markdown-body entry-content container-lg'}
            )
            if readme_element is None:
                return 'Unknown', None

            readme_content = readme_element.get_text().lower()

            keyword = self.check_keywords(readme_content, self.batch_keywords)
            if keyword:
                return 'Batch', keyword
            keyword = self.check_keywords(readme_content, self.web_service_keywords)
            if keyword:
                return 'Web Service', keyword
            keyword = self.check_keywords(readme_content, self.streaming_keywords)
            if keyword:
                return 'Streaming', keyword

            return 'Unknown', None
        except requests.exceptions.RequestException as e:
            print(f"Error checking deployment for URL {url}: {e}")
            return 'Error', None
