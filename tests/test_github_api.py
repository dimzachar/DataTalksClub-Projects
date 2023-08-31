from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class TestGitHubAPI:
    def setup_method(self):
         # Get the GitHub token from environment variables
        github_token = os.environ.get("GITHUB_ACCESS_TOKEN")
        
        github_api = GitHubAPI(github_token)
        self.github_api = GitHubAPI()

    def test_get_readme_content(self):
        content = self.github_api.get_readme_content('some_github_url')
        assert content is not None
