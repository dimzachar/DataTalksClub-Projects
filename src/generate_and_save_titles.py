import os
import logging

import pandas as pd
from dotenv import load_dotenv

from utils.github_api import GitHubAPI
from utils.openai_api import OpenAIAPI
from utils.csv_handler import CSVHandler
from utils.github_url_constructor import GithubURLConstructor

from .config import titles_csv_path, cleaned_csv_path

load_dotenv()

print("Debug: GITHUB_ACCESS_TOKEN:", os.environ.get('GITHUB_ACCESS_TOKEN'))
print("Debug: OPENAI_API_KEY:", os.environ.get('OPENAI_API_KEY'))

logging.basicConfig(
    filename='your_log_file.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)


def main():
    csv_handler = CSVHandler(cleaned_csv_path)

    if 'project_title' not in csv_handler.df.columns:
        csv_handler.df['project_title'] = None
    print("Generating summaries and titles...")
    # Initialize APIs
    github_api = GitHubAPI(os.environ.get('GITHUB_ACCESS_TOKEN'))
    openai_api = OpenAIAPI(os.environ.get('OPENAI_API_KEY'))
    print(f"Debug: Github API key is {github_api}")
    print(f"Debug: OpenAI API key is {openai_api}")
    print(f"Total URLs to Process: {len(csv_handler.df)}")
    url_constructor = GithubURLConstructor()

    def truncate_text(text, max_characters=3500):
        return text[:max_characters]

    titles = []

    for index, row in csv_handler.df.iterrows():
        # logging.info(f"Debug: Index: {index}, Row Data: {row}")

        if '/tree/' in row['project_url']:
            github_url = url_constructor.construct_readme_api_url(row['project_url'])
            # logging.info(f"Constructed URL using GithubURLConstructor: {github_url}")
        else:
            project_url = row['project_url'].split('github.com/')[-1]
            if project_url.endswith('.git'):
                project_url = project_url[:-4]
            project_url = project_url.rstrip('/')
            github_url = f"https://api.github.com/repos/{project_url}/readme"
            # logging.info(f"Constructed URL manually: {github_url}")

        # logging.info(f"Original URL: {row['project_url']}")
        # logging.info(f"Constructed URL: {github_url}")

        # print(f"Processing URL {index+1}/{len(csv_handler.df)}: {github_url}")

        if pd.notnull(row['project_title']):
            print(f"Project title already exists for {github_url}. Skipping.")
            titles.append(row['project_title'])
            continue

        readme_content = github_api.get_readme_content(github_url)
        # logging.info(
        #     f"GitHub API Response: {readme_content if readme_content else 'None'}"
        # )
        if not readme_content:
            print(f"No README content found for {github_url}. Skipping.")
            logging.warning(f"No README content found for {github_url}. Skipping.")
            titles.append("Unknown")
            continue

        # Truncate the README content
        readme_content = truncate_text(readme_content)
        summary = openai_api.generate_summary(readme_content)
        # Generate multiple titles
        multiple_titles = openai_api.generate_multiple_titles(summary)
        print(f"Generated multiple titles for {row['project_url']}: {multiple_titles}")

        # Evaluate and revise titles
        feedback, best_title = openai_api.evaluate_and_revise_titles(multiple_titles)
        print(f"Evaluation Feedback: {feedback}")
        print(f"Best Revised Title: {best_title}")

        titles.append(best_title)
        # title = openai_api.generate_title(summary)
        # print(f"Generated title for {row['project_url']}: {title}")
        # titles.append(title)

    csv_handler.update_titles(titles)

    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        '"', ''
    )

    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        'Predictor', 'Prediction'
    )
    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        'Detection', 'Prediction'
    )
    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        'Classifier', 'Classification'
    )

    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        'Title: ', ''
    )
    csv_handler.save(titles_csv_path)
    print("Title generation completed.")


if __name__ == "__main__":
    main()
