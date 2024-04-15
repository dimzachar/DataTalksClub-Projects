import os

# Define base and subdirectories
base_path = "Data"
course = "dezoomcamp"
year = 2024

subdirectory = os.path.join(base_path, course, str(year))  # More robust path joining

# Ensure the directory exists
os.makedirs(subdirectory, exist_ok=True)  # Simplifies directory creation check

# Define paths
base_name = f"scraped_{course}_{year}"
output_prefix = f"projects_{course}_{year}"
cleaned_csv_path = os.path.join(subdirectory, f"cleaned_{base_name}.csv")
titles_csv_path = os.path.join(subdirectory, f"{output_prefix}_cleaned_titles.csv")
deploy_csv_path = os.path.join(subdirectory, "data.csv")
