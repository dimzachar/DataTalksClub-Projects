import os

# Define base and subdirectories
base_path = "Data"
course = "dezoomcamp"
year = 2023

# Construct full paths
subdirectory = f"{base_path}/{course}/{year}"
base_name = f"scraped_{course}_{year}"
output_prefix = f"projects_{course}_{year}"

# Create the subdirectory if it doesn't exist
if not os.path.exists(subdirectory):
    os.makedirs(subdirectory)

# Paths for various CSV files
cleaned_csv_path = f"{subdirectory}/cleaned_{base_name}.csv"
titles_csv_path = f"{subdirectory}/{output_prefix}_cleaned_titles.csv"
deploy_csv_path = "data.csv"
