import logging


class GithubURLConstructor:
    def __init__(self):
        pass

    def construct_readme_api_url(self, project_url):
        # logging.info(f"Original URL: {project_url}")

        # Normalize the URL
        project_url = project_url.replace('https://GitHub.com/', 'https://github.com/')
        # logging.info(f"Normalized URL: {project_url}")

        if 'github.com/' not in project_url:
            logging.warning("Not a GitHub URL. Skipping.")
            return None

        # Split the URL into parts
        project_url_parts = project_url.split('github.com/')[-1].split('/')
        owner = project_url_parts[0]
        repo = project_url_parts[1]
        # logging.info(f"Owner: {owner}, Repo: {repo}")

        # Check if there are additional path elements beyond the repo name
        additional_path = '/'.join(project_url_parts[2:])
        # logging.info(f"Additional Path before cleaning: {additional_path}")

        # Remove 'tree/' and 'blob/' if present, as they're not needed in the API URL
        additional_path = additional_path.replace('tree/', '', 1).replace(
            'blob/', '', 1
        )
        # logging.info(
        #     f"Additional Path after removing 'tree/' and 'blob/': {additional_path}"
        # )

        # Remove the 'main/' or 'master/' part of the path, if present
        additional_path = additional_path.replace('main/', '', 1).replace(
            'master/', '', 1
        )
        # logging.info(
        #     f"Additional Path after removing 'main/' and 'master/': {additional_path}"
        # )

        # Construct the API URL
        if additional_path:
            readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{additional_path}/README.md"
        else:
            readme_api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"

        # logging.info(f"Constructed URL: {readme_api_url}")
        return readme_api_url
