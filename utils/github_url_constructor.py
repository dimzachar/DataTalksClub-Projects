class GithubURLConstructor:
    def __init__(self):
        pass

    def construct_readme_api_url(self, project_url):
        project_url = project_url.replace('https://GitHub.com/', 'https://github.com/')

        if 'github.com/' not in project_url:
            print("Not a GitHub URL. Skipping.")
            return None

        project_url_parts = project_url.split('github.com/')[-1].split('/')
        owner = project_url_parts[0]
        repo = project_url_parts[1]

        # Check if there are additional path elements beyond the repo name
        additional_path = '/'.join(project_url_parts[2:])

        # If the path includes "tree/", remove it to get the actual path
        additional_path = additional_path.replace('tree/', '', 1)

        # Remove the 'main/' or 'master/' part of the path, if present
        additional_path = additional_path.replace('main/', '', 1)
        additional_path = additional_path.replace('master/', '', 1)

        if additional_path:
            # If there's an additional path, include it in the API URL
            readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{additional_path}/README.md"
        else:
            # Otherwise, just point to the root README
            readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"

        print(f"Constructed URL: {readme_api_url}")
        return readme_api_url
