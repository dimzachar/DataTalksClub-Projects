import os
from utils.csv_handler import CSVHandler
from config import base_path, course, year


def main():

    base_name = f"scraped_{course}_{year}"

    combined_csv_path = os.path.join(base_path, f"{base_name}.csv")
    cleaned_csv_path = os.path.join(base_path, f"cleaned_{base_name}.csv")

    csv_handler = CSVHandler(combined_csv_path)
    csv_handler.clean_and_deduplicate('project_url')
    csv_handler.save(cleaned_csv_path)
    print(f"Saved cleaned CSV to {cleaned_csv_path}")


if __name__ == "__main__":
    main()
