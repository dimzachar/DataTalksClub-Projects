import pandas as pd


def fix_mojibake(text):
    """Fix UTF-8 text that was incorrectly decoded as Latin-1.

    Common mojibake patterns:
    - 'Ã£' should be 'ã' (São Paulo -> São Paulo)
    - 'â€' various quote marks
    - 'Â' padding character
    """
    if pd.isnull(text) or not isinstance(text, str):
        return text
    try:
        if 'Ã' in text or 'â€' in text or 'Â' in text:
            text = text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return text


class CSVHandler:
    def __init__(self, data):
        if isinstance(data, str):
            self.df = pd.read_csv(data)
        elif isinstance(data, pd.DataFrame):
            self.df = data
        else:
            raise ValueError("Input must be either a file path or a pandas DataFrame")

    def update_titles(self, titles):
        self.df['project_title'] = titles

    def save(self, new_path):
        self.df.to_csv(new_path, index=False)

    def clean_and_deduplicate(self, column_name='project_url'):
        self.df = self.df.dropna(how='all')

        if column_name in self.df.columns:
            self.df = self.df[[column_name]].copy()
        else:
            print(f"Warning: '{column_name}' not found in columns, skipping.")
            return

        # Remove duplicates
        self.df = self.df.drop_duplicates()

    def fix_mojibake_columns(self, columns):
        """Apply mojibake fix to specified text columns."""
        for col in columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].apply(fix_mojibake)
