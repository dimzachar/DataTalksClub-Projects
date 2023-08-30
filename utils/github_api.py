import os
import base64

import requests


class GitHubAPI:
    def __init__(self, token):
        self.token = token

    def get_readme_content(self, github_url):
        headers = {'Authorization': f'token {self.token}'}
        response = requests.get(github_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        readme_content_base64 = response.json()['content']
        readme_content = base64.b64decode(readme_content_base64).decode('utf-8')
        return readme_content
