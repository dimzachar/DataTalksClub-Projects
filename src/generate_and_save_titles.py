import os

import pandas as pd

from utils.github_api import GitHubAPI
from utils.openai_api import OpenAIAPI
from utils.csv_handler import CSVHandler


def main():
    titles_csv_path = os.path.join("Data", "scraped", "titles_output.csv")
    csv_handler = CSVHandler(titles_csv_path)

    # Initialize APIs
    github_api = GitHubAPI(os.environ.get('GITHUB_ACCESS_TOKEN'))
    openai_api = OpenAIAPI(os.environ.get('OPENAI_API_KEY'))

    titles = []

    for index, row in csv_handler.df.iterrows():
        print(f"Processing URL {index + 1}/{len(csv_handler.df)}: {row['project_url']}")

        if pd.notnull(row['project_title']):
            print(f"Project title already exists for {row['project_url']}. Skipping.")
            titles.append(row['project_title'])
            continue

        readme_content = github_api.get_readme_content(row['project_url'])
        if not readme_content:
            print(f"No README content found for {row['project_url']}. Skipping.")
            titles.append("Unknown")
            continue

        summary = openai_api.generate_summary(readme_content)
        title = openai_api.generate_title(summary)
        print(f"Generated title for {row['project_url']}: {title}")
        titles.append(title)

    csv_handler.update_titles(titles)
    csv_handler.save(titles_csv_path)
    print("Title generation completed.")


if __name__ == "__main__":
    main()
