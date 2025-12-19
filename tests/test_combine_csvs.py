"""Unit tests for combine_csvs module."""

import os
import tempfile
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.combine_csvs import combine_files


class TestCombineFiles:
    """Tests for combine_files function."""

    def test_combines_multiple_csvs(self, tmp_path):
        # Create test CSV files
        df1 = pd.DataFrame({'project_url': ['url1', 'url2']})
        df2 = pd.DataFrame({'project_url': ['url3', 'url4']})

        df1.to_csv(tmp_path / "file1.csv", index=False)
        df2.to_csv(tmp_path / "file2.csv", index=False)

        result = combine_files(str(tmp_path))

        assert len(result) == 4
        assert 'url1' in result['project_url'].values
        assert 'url4' in result['project_url'].values

    def test_handles_single_csv(self, tmp_path):
        df = pd.DataFrame({'project_url': ['url1']})
        df.to_csv(tmp_path / "single.csv", index=False)

        result = combine_files(str(tmp_path))

        assert len(result) == 1

    def test_raises_on_empty_directory(self, tmp_path):
        with pytest.raises(ValueError, match="No CSV files found"):
            combine_files(str(tmp_path))

    def test_ignores_non_csv_files(self, tmp_path):
        df = pd.DataFrame({'project_url': ['url1']})
        df.to_csv(tmp_path / "data.csv", index=False)

        # Create non-CSV file
        (tmp_path / "readme.txt").write_text("Not a CSV")

        result = combine_files(str(tmp_path))

        assert len(result) == 1

    def test_preserves_all_columns(self, tmp_path):
        df1 = pd.DataFrame({'project_url': ['url1'], 'extra_col': ['value1']})
        df2 = pd.DataFrame({'project_url': ['url2'], 'extra_col': ['value2']})

        df1.to_csv(tmp_path / "file1.csv", index=False)
        df2.to_csv(tmp_path / "file2.csv", index=False)

        result = combine_files(str(tmp_path))

        assert 'extra_col' in result.columns
        assert len(result) == 2

    def test_handles_different_columns(self, tmp_path):
        df1 = pd.DataFrame({'project_url': ['url1'], 'col_a': ['a']})
        df2 = pd.DataFrame({'project_url': ['url2'], 'col_b': ['b']})

        df1.to_csv(tmp_path / "file1.csv", index=False)
        df2.to_csv(tmp_path / "file2.csv", index=False)

        result = combine_files(str(tmp_path))

        # pandas concat fills missing columns with NaN
        assert len(result) == 2
        assert 'col_a' in result.columns
        assert 'col_b' in result.columns


class TestCombineCSVsMain:
    """Tests for combine_csvs main function."""

    @patch('src.combine_csvs.get_config')
    @patch('src.combine_csvs.CSVHandler')
    @patch('src.combine_csvs.combine_files')
    def test_main_workflow(
        self, mock_combine, mock_handler_class, mock_config, tmp_path
    ):
        # Setup mocks
        mock_config.return_value = {
            'subdirectory': str(tmp_path),
            'cleaned_csv_path': str(tmp_path / 'cleaned.csv'),
        }

        mock_df = pd.DataFrame({'project_url': ['url1', 'url2']})
        mock_combine.return_value = mock_df

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        # Import and run main
        from src.combine_csvs import main

        main()

        # Verify workflow
        mock_combine.assert_called_once_with(str(tmp_path))
        mock_handler.clean_and_deduplicate.assert_called_once_with('project_url')
        mock_handler.save.assert_called_once()
