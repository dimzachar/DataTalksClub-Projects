import os

import pandas as pd
from dotenv import load_dotenv

from utils.csv_handler import CSVHandler

from .config import get_config

load_dotenv()


def combine_files(directory):
    """
    Combine all CSV files in the given directory and remove duplicates.
    """
    all_dataframes = []
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            file_path = os.path.join(directory, filename)
            df = pd.read_csv(file_path)
            all_dataframes.append(df)

    if not all_dataframes:
        raise ValueError(f"No CSV files found in directory: {directory}")

    combined_df = pd.concat(all_dataframes, ignore_index=True)
    return combined_df


def main():

    config = get_config()
    combined_df = combine_files(config['subdirectory'])
    csv_handler = CSVHandler(combined_df)
    csv_handler.clean_and_deduplicate('project_url')
    csv_handler.save(config['cleaned_csv_path'])

    print(f"Combined and cleaned CSV saved to {config['cleaned_csv_path']}")


if __name__ == "__main__":
    main()
