import os
import argparse

# Course-specific valid deployment types
COURSE_DEPLOYMENT_TYPES = {
    'dezoomcamp': ['Batch', 'Streaming'],  # Data Engineering: only Batch or Streaming
    'mlzoomcamp': [
        'Batch',
        'Web Service',
        'Streaming',
    ],  # ML: Batch training + Web Service for inference
    'mlopszoomcamp': ['Batch', 'Web Service', 'Streaming'],  # MLOps: similar to ML
    'llmzoomcamp': ['Batch', 'Web Service', 'Streaming'],  # LLM: Batch + API serving
}


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
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Limit number of projects to process (0 = all)',
    )
    parser.add_argument(
        '--workers', type=int, default=5, help='Number of parallel workers (default: 5)'
    )

    args = parser.parse_args()

    course = args.course
    year = args.year
    base_path = args.base_path

    subdirectory = os.path.join(base_path, course, str(year))
    os.makedirs(subdirectory, exist_ok=True)

    output_prefix = f"projects_{course}_{year}"

    # Get valid deployment types for this course
    valid_deployment_types = COURSE_DEPLOYMENT_TYPES.get(
        course, ['Batch', 'Streaming', 'Web Service']  # Default: all types
    )

    return {
        "base_path": base_path,
        "course": course,
        "year": year,
        "limit": args.limit,
        "max_workers": args.workers,
        "valid_deployment_types": valid_deployment_types,
        "subdirectory": subdirectory,
        "cleaned_csv_path": os.path.join(
            subdirectory, f"cleaned_scraped_{course}_{year}.csv"
        ),
        "titles_csv_path": os.path.join(
            subdirectory, f"{output_prefix}_cleaned_titles.csv"
        ),
        "deploy_csv_path": os.path.join(subdirectory, "data.csv"),
    }
