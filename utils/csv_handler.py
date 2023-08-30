import pandas as pd


class CSVHandler:
    def __init__(self, csv_path):
        self.df = pd.read_csv(csv_path)

    def update_titles(self, titles):
        print(f"Debug: Updating titles in CSVHandler with {titles}")
        self.df['project_title'] = titles

    def save(self, new_path):
        self.df.to_csv(new_path, index=False)

    def clean_and_deduplicate(self, column_name='project_url'):
        # Drop rows where all elements are NaN
        self.df = self.df.dropna(how='all')

        # Keep only the relevant column and copy it to a new DataFrame
        if column_name in self.df.columns:
            self.df = self.df[[column_name]].copy()
        else:
            print(f"Warning: '{column_name}' not found in columns, skipping.")
            return

        # Remove duplicates
        self.df = self.df.drop_duplicates()
