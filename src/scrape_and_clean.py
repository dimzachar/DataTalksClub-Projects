import os
import re

import pandas as pd
from dotenv import load_dotenv

from config import year, course, base_path
from utils.csv_handler import CSVHandler

subdirectory = f"{base_path}/{course}/{year}"

load_dotenv()


def main():
    csv_files = [
        f
        for f in os.listdir(subdirectory)
        if f.endswith('.csv') and re.search(r'cleaned_scraped_', f)
    ]
    if not csv_files:
        print(f"Error: No cleaned CSV files found in {subdirectory}. Exiting.")
        return

    csv_path = os.path.join(subdirectory, csv_files[0])
    print("CSV Path is:", csv_path)

    if not os.path.exists(subdirectory):
        os.makedirs(subdirectory)

    cleaned_csv_path = os.path.join(
        subdirectory, f"cleaned_scraped_{course}_{year}.csv"
    )

    csv_handler = CSVHandler(csv_path)
    csv_handler.clean_and_deduplicate('project_url')
    csv_handler.save(cleaned_csv_path)

    print(f"Saved cleaned CSV to {cleaned_csv_path}")


if __name__ == "__main__":
    main()
