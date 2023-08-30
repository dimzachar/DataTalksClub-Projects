import os

from utils.scraping_handler import ScrapingHandler
from config import base_path, course, year

def main():

    sheet_url = os.environ.get("SHEET_URL", None)
    if not sheet_url:
        print("Error: No SHEET_URL environment variable found. Exiting.")
        return

    scraper = ScrapingHandler(sheet_url, base_path, course, year)
    num_tabs = scraper.scrape_data()
    print(f"Web scraping completed. Number of tabs scraped: {num_tabs}")


if __name__ == "__main__":
    main()
