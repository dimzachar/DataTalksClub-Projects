import os
import json

import pandas as pd
from dotenv import load_dotenv

from utils.csv_handler import CSVHandler
from utils.scraping_handler import ScrapingHandler

from .config import year, course, base_path

# Load environment variables from .env file
load_dotenv()


def main():
    # Perform Data Scraping
    sheet_urls_str = os.environ.get("SHEET_URLS", None)
    sheet_urls = json.loads(sheet_urls_str) if sheet_urls_str else []
    print(sheet_urls)
    if not sheet_urls:
        print("Error: No SHEET_URL environment variable found. Exiting.")
        return

    list_of_dfs = []
    for index, sheet_url in enumerate(sheet_urls):
        scraper = ScrapingHandler(sheet_url, base_path, course, year)
        scraped_files = scraper.scrape_data()
        print(
            f"Web scraping completed for {sheet_url}. Number of tabs scraped: {scraped_files}"
        )

        if not scraped_files:
            continue

        subdirectory = scraper.subdirectory
        for file_name in scraped_files:
            csv_file = os.path.join(subdirectory, file_name)
            df = pd.read_csv(csv_file, skiprows=1)
            list_of_dfs.append(df)

    # Combine all dataframes
    combined_df = pd.concat(list_of_dfs, ignore_index=True)

    # Save the combined DataFrame to a temporary CSV
    combined_csv_path = os.path.join(subdirectory, "temporary_combined.csv")
    combined_df.to_csv(combined_csv_path, index=False)

    # Clean and save the combined CSV
    cleaned_csv_path = os.path.join(
        subdirectory, f"cleaned_scraped_{course}_{year}.csv"
    )
    csv_handler = CSVHandler(combined_csv_path)
    csv_handler.clean_and_deduplicate('project_url')
    csv_handler.save(cleaned_csv_path)

    # Delete the temporary combined CSV
    os.remove(combined_csv_path)

    print(f"Saved cleaned CSV to {cleaned_csv_path}")


if __name__ == "__main__":
    main()
