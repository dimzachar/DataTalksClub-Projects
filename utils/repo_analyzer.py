"""
Repository analyzer that fetches multiple key files for better context.
Inspired by ZoomJudge approach but simplified for speed.
"""

import os
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Suppress INFO logs


class RepoAnalyzer:
    """Fetches and analyzes multiple files from a GitHub repository."""

    # Key files to fetch (high value for classification and title generation)
    KEY_FILES = [
        'README.md',
        'readme.md',
        'README',
        'docker-compose.yml',
        'docker-compose.yaml',
        'requirements.txt',
        'pyproject.toml',
        'Dockerfile',
        'Makefile',
        'setup.py',
    ]

    # Patterns that indicate important files/directories
    KEY_PATTERNS = [
        '.tf',  # Terraform = definitive cloud indicator
        'dags/',  # Airflow DAGs = batch
        'terraform/',  # Terraform configs
        'airflow/',  # Airflow configs
        'kafka',  # Kafka = streaming
        'flink',  # Flink = streaming
        'kestra',  # Kestra = batch orchestrator
        'prefect',  # Prefect = batch orchestrator
        'mage',  # Mage = batch orchestrator
    ]

    # Files to exclude
    EXCLUDED_EXTENSIONS = {
        '.png',
        '.jpg',
        '.jpeg',
        '.gif',
        '.svg',
        '.ico',
        '.webp',
        '.pdf',
        '.zip',
        '.gz',
        '.tar',
        '.rar',
        '.csv',
        '.parquet',
        '.pkl',
        '.h5',
        '.bin',
        '.exe',
        '.dll',
        '.so',
        '.lock',
        '.log',
        '.mp3',
        '.mp4',
        '.wav',
        '.avi',
    }

    def __init__(self, github_token: str = None):
        self.token = github_token or os.environ.get('MY_GITHUB_TOKEN')
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

    def parse_github_url(self, url: str) -> tuple:
        """Extract owner, repo, and subpath from GitHub URL.

        Returns:
            tuple: (owner, repo, subpath) where subpath is the nested directory or None
        """
        url = url.rstrip('/')
        subpath = None

        # Handle /tree/branch/path URLs (nested project directories)
        if '/tree/' in url:
            base_url, tree_part = url.split('/tree/', 1)
            # tree_part is like "main/project" or just "main"
            tree_parts = tree_part.split('/', 1)
            if len(tree_parts) > 1:
                subpath = tree_parts[1]  # e.g., "project" or "Project"
            url = base_url

        # Remove .git suffix
        if url.endswith('.git'):
            url = url[:-4]

        # Extract owner/repo
        parts = url.replace('https://github.com/', '').split('/')
        if len(parts) >= 2:
            return parts[0], parts[1], subpath
        return None, None, None

    def get_repo_tree(self, owner: str, repo: str) -> list:
        """Fetch repository file tree via GitHub API."""
        for branch in ['main', 'master']:
            url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1'
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.ok:
                    tree = resp.json().get('tree', [])
                    return [item['path'] for item in tree if item['type'] == 'blob']
            except Exception as e:
                logger.debug(f"Error fetching tree for {branch}: {e}")
        return []

    def fetch_file_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch content of a single file."""
        url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.ok:
                data = resp.json()
                if data.get('type') == 'file' and data.get('content'):
                    content = base64.b64decode(data['content']).decode(
                        'utf-8', errors='replace'
                    )
                    return content[:8000]  # Truncate large files
        except Exception as e:
            logger.debug(f"Error fetching {path}: {e}")
        return None

    def _should_fetch_file(self, filepath: str, subpath: str = None) -> bool:
        """Check if file should be fetched based on patterns.

        Args:
            filepath: Full path to file in repo
            subpath: If set, only fetch files within this subdirectory
        """
        fp_lower = filepath.lower()

        # If subpath is specified, only fetch files within that directory
        if subpath:
            subpath_lower = subpath.lower()
            if (
                not fp_lower.startswith(subpath_lower + '/')
                and fp_lower != subpath_lower
            ):
                # Allow root-level config files even outside subpath
                if '/' in filepath:
                    return False

        # Exclude binary/media files
        if any(fp_lower.endswith(ext) for ext in self.EXCLUDED_EXTENSIONS):
            return False

        # Exclude common non-useful paths
        if any(
            x in fp_lower
            for x in ['/node_modules/', '/__pycache__/', '/.git/', '/venv/', '/.venv/']
        ):
            return False

        # Check if it's a key file
        filename = filepath.split('/')[-1].lower()
        if any(kf.lower() in filename for kf in self.KEY_FILES):
            return True

        # Check if it matches key patterns
        if any(pattern in fp_lower for pattern in self.KEY_PATTERNS):
            return True

        return False

    def fetch_key_files(
        self, owner: str, repo: str, subpath: str = None, max_files: int = 10
    ) -> dict:
        """Fetch content of key files from repository.

        Args:
            owner: GitHub repo owner
            repo: GitHub repo name
            subpath: If set, prioritize files within this subdirectory (for nested projects)
            max_files: Maximum number of files to fetch
        """
        content = {}

        # Get repo tree
        tree = self.get_repo_tree(owner, repo)
        if not tree:
            logger.warning(f"Could not fetch tree for {owner}/{repo}")
            return content

        # Filter to key files, respecting subpath
        files_to_fetch = [f for f in tree if self._should_fetch_file(f, subpath)]

        # Prioritize files within subpath, then by depth
        def sort_key(filepath):
            in_subpath = 0
            if subpath and filepath.lower().startswith(subpath.lower() + '/'):
                in_subpath = -1  # Prioritize subpath files
            return (in_subpath, filepath.count('/'), filepath)

        files_to_fetch.sort(key=sort_key)
        files_to_fetch = files_to_fetch[:max_files]

        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_path = {
                executor.submit(self.fetch_file_content, owner, repo, f): f
                for f in files_to_fetch
            }
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_content = future.result()
                    if file_content:
                        content[path] = file_content
                except Exception as e:
                    logger.debug(f"Error fetching {path}: {e}")

        return content

    def analyze_repo(self, github_url: str) -> dict:
        """
        Analyze a GitHub repository and return key file contents.

        Returns:
            dict with keys:
                - files: dict of {filepath: content}
                - owner: repo owner
                - repo: repo name
                - subpath: nested project directory (if any)
        """
        owner, repo, subpath = self.parse_github_url(github_url)
        if not owner or not repo:
            logger.error(f"Could not parse GitHub URL: {github_url}")
            return {'files': {}, 'owner': None, 'repo': None, 'subpath': None}

        files = self.fetch_key_files(owner, repo, subpath)

        return {
            'files': files,
            'owner': owner,
            'repo': repo,
            'subpath': subpath,
        }

    def format_content_for_llm(self, files: dict, max_chars: int = 15000) -> str:
        """Format file contents for LLM prompt."""
        formatted = ""
        for filepath, content in files.items():
            # Truncate individual files
            truncated = content[:4000] if len(content) > 4000 else content
            formatted += f"\n--- {filepath} ---\n{truncated}\n"

            if len(formatted) > max_chars:
                formatted = formatted[:max_chars] + "\n[truncated...]"
                break

        return formatted
