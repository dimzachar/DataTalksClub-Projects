import os

import pandas as pd


def validate_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        required_columns = ['project_url']
        for col in required_columns:
            if col not in df.columns:
                print(f"Validation failed: Missing column {col} in {file_path}")
                return False
        print(f"Validation passed for {file_path}")
        return True
    except Exception as e:
        print(f"Validation failed for {file_path}: {e}")
        return False


def main():
    pr_files = os.getenv('PR_FILES', '').split(',')
    for file_path in pr_files:
        if file_path.endswith('.csv'):
            if not validate_csv(file_path):
                exit(1)


if __name__ == "__main__":
    main()
