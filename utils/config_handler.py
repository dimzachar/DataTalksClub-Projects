import os


def get_config(csv_path):
    parts = csv_path.split('/')
    if len(parts) < 4:
        raise ValueError("Invalid CSV path format")

    base_path = "/".join(parts[:-3])
    course = parts[-3]
    year = parts[-2]

    subdirectory = os.path.join(base_path, course, year)
    os.makedirs(subdirectory, exist_ok=True)

    base_name = f"scraped_{course}_{year}"
    output_prefix = f"projects_{course}_{year}"

    return {
        "base_path": base_path,
        "course": course,
        "year": year,
        "subdirectory": subdirectory,
        "cleaned_csv_path": os.path.join(subdirectory, f"cleaned_{base_name}.csv"),
        "titles_csv_path": os.path.join(
            subdirectory, f"{output_prefix}_cleaned_titles.csv"
        ),
        "deploy_csv_path": os.path.join(subdirectory, "data.csv"),
    }
