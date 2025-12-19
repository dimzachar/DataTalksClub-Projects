"""Unit tests for CSVHandler utility."""

import os
import tempfile

import pandas as pd
import pytest

from utils.csv_handler import CSVHandler


class TestCSVHandlerInit:
    """Tests for CSVHandler initialization."""

    def test_init_from_dataframe(self):
        df = pd.DataFrame({'project_url': ['https://github.com/user/repo']})
        handler = CSVHandler(df)
        assert len(handler.df) == 1
        assert 'project_url' in handler.df.columns

    def test_init_from_csv_file(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        df = pd.DataFrame({'project_url': ['https://github.com/user/repo']})
        df.to_csv(csv_file, index=False)

        handler = CSVHandler(str(csv_file))
        assert len(handler.df) == 1

    def test_init_invalid_input_raises(self):
        with pytest.raises(ValueError, match="file path or a pandas DataFrame"):
            CSVHandler(12345)

    def test_init_invalid_input_list_raises(self):
        with pytest.raises(ValueError):
            CSVHandler(['not', 'a', 'dataframe'])


class TestCleanAndDeduplicate:
    """Tests for clean_and_deduplicate method."""

    def test_removes_duplicates(self):
        df = pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user/repo1',
                    'https://github.com/user/repo1',  # duplicate
                    'https://github.com/user/repo2',
                ]
            }
        )
        handler = CSVHandler(df)
        handler.clean_and_deduplicate('project_url')

        assert len(handler.df) == 2

    def test_removes_empty_rows(self):
        df = pd.DataFrame(
            {
                'project_url': ['https://github.com/user/repo', None, ''],
                'other_col': [None, None, None],
            }
        )
        handler = CSVHandler(df)
        handler.clean_and_deduplicate('project_url')

        # dropna(how='all') removes rows where ALL values are NaN
        assert len(handler.df) <= 3

    def test_keeps_only_specified_column(self):
        df = pd.DataFrame(
            {
                'project_url': ['https://github.com/user/repo'],
                'extra_column': ['should be removed'],
            }
        )
        handler = CSVHandler(df)
        handler.clean_and_deduplicate('project_url')

        assert list(handler.df.columns) == ['project_url']

    def test_handles_missing_column_gracefully(self):
        df = pd.DataFrame({'other_column': ['value']})
        handler = CSVHandler(df)
        handler.clean_and_deduplicate('project_url')
        # Should print warning but not crash
        assert 'other_column' in handler.df.columns


class TestUpdateTitles:
    """Tests for update_titles method."""

    def test_updates_titles_column(self):
        df = pd.DataFrame({'project_url': ['url1', 'url2', 'url3']})
        handler = CSVHandler(df)
        titles = ['Title 1', 'Title 2', 'Title 3']

        handler.update_titles(titles)

        assert list(handler.df['project_title']) == titles

    def test_overwrites_existing_titles(self):
        df = pd.DataFrame({'project_url': ['url1'], 'project_title': ['Old Title']})
        handler = CSVHandler(df)

        handler.update_titles(['New Title'])

        assert handler.df['project_title'].iloc[0] == 'New Title'


class TestSave:
    """Tests for save method."""

    def test_saves_to_csv(self, tmp_path):
        df = pd.DataFrame(
            {
                'project_url': ['https://github.com/user/repo'],
                'project_title': ['Test Title'],
            }
        )
        handler = CSVHandler(df)
        output_path = tmp_path / "output.csv"

        handler.save(str(output_path))

        assert output_path.exists()
        loaded = pd.read_csv(output_path)
        assert len(loaded) == 1
        assert loaded['project_title'].iloc[0] == 'Test Title'

    def test_saves_without_index(self, tmp_path):
        df = pd.DataFrame({'col': ['value']})
        handler = CSVHandler(df)
        output_path = tmp_path / "output.csv"

        handler.save(str(output_path))

        loaded = pd.read_csv(output_path)
        assert 'Unnamed: 0' not in loaded.columns


class TestCSVHandlerIntegration:
    """Integration tests for CSVHandler workflow."""

    def test_full_workflow(self, tmp_path):
        # Create initial CSV
        input_csv = tmp_path / "input.csv"
        df = pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user/repo1',
                    'https://github.com/user/repo1',  # duplicate
                    'https://github.com/user/repo2',
                ],
                'extra': ['a', 'b', 'c'],
            }
        )
        df.to_csv(input_csv, index=False)

        # Process
        handler = CSVHandler(str(input_csv))
        handler.clean_and_deduplicate('project_url')
        handler.update_titles(['Title 1', 'Title 2'])

        output_csv = tmp_path / "output.csv"
        handler.save(str(output_csv))

        # Verify
        result = pd.read_csv(output_csv)
        assert len(result) == 2
        assert 'project_title' in result.columns
        assert 'extra' not in result.columns
