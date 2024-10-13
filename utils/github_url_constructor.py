import os
import logging
from urllib.parse import urlparse

import requests

headers = {"Authorization": f"token {os.environ.get('MY_GITHUB_TOKEN')}"}
print(headers)


class GithubURLConstructor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def sanitize_url(self, url):
        parsed_url = urlparse(url)
        return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

    def get_readme_filename(self, owner, repo, additional_path):
        """Get the actual case of the README file from the GitHub API."""
        api_url = (
            f"https://api.github.com/repos/{owner}/{repo}/contents/{additional_path}"
        )
        self.logger.debug(f"Fetching content from API URL: {api_url}")

        response = requests.get(api_url, headers=headers, timeout=20)
        if response.status_code == 200:
            content = response.json()

            if (
                isinstance(content, dict)
                and content.get('name', '').lower() == 'readme.md'
            ):
                self.logger.info(f"Directly fetched README file: {content['name']}")
                return content['name']

            elif isinstance(content, list):
                for file in content:
                    if file['type'] == 'file' and file['name'].lower() == 'readme.md':
                        self.logger.info(
                            f"Found README file in the list: {file['name']}"
                        )
                        return file['name']

        else:
            self.logger.warning(
                f"Failed to fetch content from API URL: {api_url}. Status code: {response.status_code}"
            )

        self.logger.info("README file not found.")
        return None

    def construct_readme_api_url(self, project_url):
        project_url = self.sanitize_url(project_url)
        self.logger.info(f"Original URL: {project_url}")

        project_url = project_url.replace('https://GitHub.com/', 'https://github.com/')
        self.logger.info(f"Normalized URL: {project_url}")

        if 'github.com/' not in project_url:
            self.logger.warning(f"Not a GitHub URL. Skipping: {project_url}")
            return None, None

        project_url_parts = project_url.split('github.com/')[-1].split('/')

        if len(project_url_parts) < 2:
            self.logger.warning(f"Invalid GitHub URL format. Skipping: {project_url}")
            return None, None

        owner, repo = project_url_parts[:2]
        repo = repo.replace('.git', '')

        self.logger.info(f"Owner: {owner}, Repo: {repo}")

        if 'README.md' in project_url_parts:
            readme_api_url = (
                f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
            )
            self.logger.info(f"Constructed URL: {readme_api_url}")
            return readme_api_url, None

        branch = None
        if 'tree' in project_url_parts:
            branch_index = project_url_parts.index('tree')
            branch = project_url_parts[branch_index + 1]
            additional_path_parts = project_url_parts[branch_index + 2 :]
        elif 'blob' in project_url_parts:
            branch_index = project_url_parts.index('blob')
            branch = project_url_parts[branch_index + 1]
            additional_path_parts = project_url_parts[branch_index + 2 :]
        else:
            additional_path_parts = project_url_parts[2:]

        additional_path = '/'.join(additional_path_parts)

        self.logger.info(f"Branch: {branch}, Additional Path: {additional_path}")

        readme_filename = self.get_readme_filename(owner, repo, additional_path)
        if not readme_filename:
            self.logger.warning("README file not found in the repository.")
            return None, None

        readme_api_url_with_main = f"https://api.github.com/repos/{owner}/{repo}/contents/{additional_path}/{readme_filename}"
        additional_path = (
            additional_path.replace(f'{branch}/', '', 1) if branch else additional_path
        )
        self.logger.info(f"Additional Path without branch: {additional_path}")
        readme_api_url_without_main = f"https://api.github.com/repos/{owner}/{repo}/contents/{additional_path}/{readme_filename}"

        self.logger.info(
            f"Constructed URLs: {readme_api_url_with_main}, {readme_api_url_without_main}"
        )

        return readme_api_url_with_main, readme_api_url_without_main
