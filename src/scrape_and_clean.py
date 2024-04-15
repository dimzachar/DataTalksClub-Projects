import os
import pandas as pd
from dotenv import load_dotenv
from utils.csv_handler import CSVHandler
from .config import year, course, base_path

subdirectory = f"{base_path}/{course}/{year}"

# Load environment variables
load_dotenv()

def main():
    # Path to the CSV file uploaded via pull request
    csv_path = os.environ.get("CSV_PATH", None)
    print("CSV Path is:", csv_path)
    if not csv_path:
        print("Error: No CSV_PATH environment variable found. Exiting.")
        return

    # Check if subdirectory exists, if not, create it
    if not os.path.exists(subdirectory):
        os.makedirs(subdirectory)

    # Define the path for the cleaned CSV within the specified subdirectory
    cleaned_csv_path = os.path.join(subdirectory, f"cleaned_scraped_{course}_{year}.csv")

    # Initialize CSV handler and process the file
    csv_handler = CSVHandler(csv_path)
    csv_handler.clean_and_deduplicate('project_url')
    csv_handler.save(cleaned_csv_path)

    print(f"Saved cleaned CSV to {cleaned_csv_path}")

if __name__ == "__main__":
    main()
