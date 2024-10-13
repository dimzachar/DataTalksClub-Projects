import os
import argparse


def get_config():
    parser = argparse.ArgumentParser(
        description='Process course and year for data analysis.'
    )
    parser.add_argument(
        '--course', type=str, required=True, help='Course name (e.g., dezoomcamp)'
    )
    parser.add_argument('--year', type=int, required=True, help='Year of the course')
    parser.add_argument(
        '--base_path', type=str, default='Data', help='Base path for data storage'
    )

    args = parser.parse_args()

    course = args.course
    year = args.year
    base_path = args.base_path

    subdirectory = os.path.join(base_path, course, str(year))
    os.makedirs(subdirectory, exist_ok=True)

    output_prefix = f"projects_{course}_{year}"

    return {
        "base_path": base_path,
        "course": course,
        "year": year,
        "subdirectory": subdirectory,
        "cleaned_csv_path": os.path.join(
            subdirectory, f"cleaned_scraped_{course}_{year}.csv"
        ),
        "titles_csv_path": os.path.join(
            subdirectory, f"{output_prefix}_cleaned_titles.csv"
        ),
        "deploy_csv_path": os.path.join(subdirectory, "data.csv"),
    }
