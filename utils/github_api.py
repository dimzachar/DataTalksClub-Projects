import json
import base64

import requests


class GitHubAPI:
    def __init__(self, token):
        self.token = token

    def get_readme_content(self, github_url):
        headers = {'Authorization': f'token {self.token}'}
        try:
            response = requests.get(github_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(
                    f"Failed to fetch README for {github_url}. Status code: {response.status_code}"
                )
                print("Response Content:", response.content.decode())
                return None
            response_json = response.json()
            if 'content' not in response_json:
                print(f"No README content found for {github_url}.")
                return None
            readme_content_base64 = response_json['content']
            readme_content = base64.b64decode(readme_content_base64).decode('utf-8')
            return readme_content
        except requests.exceptions.RequestException as e:
            print(f"Request exception for {github_url}: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {github_url}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {github_url}: {e}")
        return None
