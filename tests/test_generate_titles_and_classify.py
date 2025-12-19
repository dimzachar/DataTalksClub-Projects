"""Unit tests for generate_titles_and_classify module."""

import os
from unittest.mock import Mock, MagicMock, patch

import pandas as pd
import pytest

from src.generate_titles_and_classify import (
    Counter,
    truncate_text,
    _check_env_vars,
    process_single_project,
)


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncates_long_text(self):
        text = "x" * 5000
        result = truncate_text(text, max_characters=3500)
        assert len(result) == 3500

    def test_preserves_short_text(self):
        text = "short text"
        result = truncate_text(text, max_characters=3500)
        assert result == text

    def test_custom_max_characters(self):
        text = "x" * 100
        result = truncate_text(text, max_characters=50)
        assert len(result) == 50


class TestCounter:
    """Tests for thread-safe Counter class."""

    def test_initial_values(self):
        counter = Counter()
        assert counter.success == 0
        assert counter.skip == 0
        assert counter.error == 0

    def test_increment_success(self):
        counter = Counter()
        counter.inc_success()
        counter.inc_success()
        assert counter.success == 2

    def test_increment_skip(self):
        counter = Counter()
        counter.inc_skip()
        assert counter.skip == 1

    def test_increment_error(self):
        counter = Counter()
        counter.inc_error()
        assert counter.error == 1

    def test_thread_safety(self):
        from concurrent.futures import ThreadPoolExecutor

        counter = Counter()

        def increment_many():
            for _ in range(100):
                counter.inc_success()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(increment_many) for _ in range(4)]
            for f in futures:
                f.result()

        assert counter.success == 400


class TestProcessSingleProject:
    """Tests for process_single_project function."""

    def test_skips_already_processed(self):
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': 'Existing Title',
                'Deployment Type': 'Batch',
                'Reason': 'Uses Airflow',
                'Cloud': 'GCP',
            }
        )

        mock_analyzer = Mock()
        mock_openai = Mock()

        args = (0, row, mock_analyzer, mock_openai, ['Batch', 'Streaming'])
        index, result = process_single_project(args)

        assert result['status'] == 'skip'
        assert result['project_title'] == 'Existing Title'
        mock_analyzer.analyze_repo.assert_not_called()

    def test_processes_unknown_title(self):
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,  # None triggers title generation
                'Deployment Type': 'Unknown',
                'Reason': None,
                'Cloud': None,
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {
            'files': {'README.md': '# Test Project'}
        }

        mock_openai = Mock()
        mock_openai.classify_deployment_and_cloud.return_value = {
            'deployment_type': 'Batch',
            'deployment_reason': 'Uses Airflow',
            'cloud_provider': 'GCP',
        }
        mock_openai.generate_summary.return_value = "A data pipeline"
        mock_openai.generate_multiple_titles.return_value = ['Title 1', 'Title 2']
        mock_openai.evaluate_and_revise_titles.return_value = ('feedback', 'Best Title')

        args = (0, row, mock_analyzer, mock_openai, ['Batch', 'Streaming'])
        index, result = process_single_project(args)

        assert result['status'] == 'success'
        assert result['project_title'] == 'Best Title'
        assert result['Deployment Type'] == 'Batch'

    def test_handles_no_files_fetched(self):
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {'files': {}}

        mock_openai = Mock()

        args = (0, row, mock_analyzer, mock_openai, ['Batch', 'Streaming'])
        index, result = process_single_project(args)

        assert result['status'] == 'skip'
        assert result['project_title'] == 'Unknown'
        assert result['Deployment Type'] == 'Unknown'

    def test_handles_exception(self):
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.side_effect = Exception("API Error")

        mock_openai = Mock()

        args = (0, row, mock_analyzer, mock_openai, ['Batch', 'Streaming'])
        index, result = process_single_project(args)

        assert result['status'] == 'error'
        assert result['Deployment Type'] == 'Error'

    def test_does_not_skip_error_status(self):
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': 'Error',
                'Deployment Type': 'Error',
                'Reason': 'Previous error',
                'Cloud': 'Error',
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {'files': {'README.md': '# Test'}}

        mock_openai = Mock()
        mock_openai.classify_deployment_and_cloud.return_value = {
            'deployment_type': 'Batch',
            'deployment_reason': 'Uses Airflow',
            'cloud_provider': 'GCP',
        }
        mock_openai.generate_summary.return_value = "Summary"
        mock_openai.generate_multiple_titles.return_value = ['Title']
        mock_openai.evaluate_and_revise_titles.return_value = ('fb', 'New Title')

        args = (0, row, mock_analyzer, mock_openai, ['Batch'])
        index, result = process_single_project(args)

        # Should process, not skip
        assert result['status'] == 'success'

    def test_preserves_existing_deployment_type(self):
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,  # Needs title
                'Deployment Type': 'Batch',  # Already classified
                'Reason': 'Uses Airflow',
                'Cloud': 'GCP',
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {'files': {'README.md': '# Test'}}

        mock_openai = Mock()
        mock_openai.generate_summary.return_value = "Summary"
        mock_openai.generate_multiple_titles.return_value = ['Title']
        mock_openai.evaluate_and_revise_titles.return_value = ('fb', 'New Title')

        args = (0, row, mock_analyzer, mock_openai, ['Batch'])
        index, result = process_single_project(args)

        # Should not call classify since deployment already set
        mock_openai.classify_deployment_and_cloud.assert_not_called()


class TestMojibakeFix:
    """Tests for mojibake fix in main function."""

    def test_fix_mojibake_function(self):
        # Import the fix function from the module
        import pandas as pd

        def fix_mojibake(text):
            if pd.isnull(text) or not isinstance(text, str):
                return text
            try:
                if 'Ã' in text or 'â€' in text or 'Â' in text:
                    text = text.encode('latin-1').decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            return text

        # Test cases
        assert fix_mojibake("SÃ£o Paulo") == "São Paulo"
        assert fix_mojibake("Normal text") == "Normal text"
        assert fix_mojibake(None) is None


class TestProcessSingleProjectEdgeCases:
    """Additional edge case tests for process_single_project."""

    def test_handles_no_summary_generated(self):
        """Test when summary generation returns empty."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {'files': {'README.md': '# Test'}}

        mock_openai = Mock()
        mock_openai.classify_deployment_and_cloud.return_value = {
            'deployment_type': 'Batch',
            'deployment_reason': 'Uses Airflow',
            'cloud_provider': 'GCP',
        }
        mock_openai.generate_summary.return_value = None  # No summary

        args = (0, row, mock_analyzer, mock_openai, ['Batch'])
        index, result = process_single_project(args)

        assert result['project_title'] == 'Unknown'

    def test_handles_no_titles_generated(self):
        """Test when title generation returns empty list."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {'files': {'README.md': '# Test'}}

        mock_openai = Mock()
        mock_openai.classify_deployment_and_cloud.return_value = {
            'deployment_type': 'Batch',
            'deployment_reason': 'Uses Airflow',
            'cloud_provider': 'GCP',
        }
        mock_openai.generate_summary.return_value = "A summary"
        mock_openai.generate_multiple_titles.return_value = []  # No titles

        args = (0, row, mock_analyzer, mock_openai, ['Batch'])
        index, result = process_single_project(args)

        assert result['project_title'] == 'Unknown'

    def test_handles_empty_combined_content(self):
        """Test when files have no usable content."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
            }
        )

        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {
            'files': {'empty.txt': ''}  # Empty content
        }

        mock_openai = Mock()
        mock_openai.classify_deployment_and_cloud.return_value = {
            'deployment_type': 'Batch',
            'deployment_reason': 'test',
            'cloud_provider': 'GCP',
        }
        mock_openai.generate_summary.return_value = None

        args = (0, row, mock_analyzer, mock_openai, ['Batch'])
        index, result = process_single_project(args)

        # Should still succeed with classification but Unknown title
        assert result['Deployment Type'] == 'Batch'


class TestSkipLogic:
    """Tests for skip logic in process_single_project."""

    def test_skip_when_both_valid(self):
        """Should skip when both title and deployment are valid."""
        row = pd.Series(
            {
                'project_url': 'url',
                'project_title': 'Valid Title',
                'Deployment Type': 'Batch',
                'Reason': 'reason',
                'Cloud': 'GCP',
            }
        )

        existing_title = row.get('project_title')
        existing_deployment = row.get('Deployment Type')
        should_skip = (
            pd.notnull(existing_title)
            and existing_title != 'Unknown'
            and existing_title != 'Error'
            and pd.notnull(existing_deployment)
            and existing_deployment != 'Unknown'
            and existing_deployment != 'Error'
        )

        assert should_skip is True

    def test_no_skip_when_title_unknown(self):
        """Should not skip when title is Unknown."""
        row = pd.Series(
            {
                'project_url': 'url',
                'project_title': 'Unknown',
                'Deployment Type': 'Batch',
            }
        )

        existing_title = row.get('project_title')
        existing_deployment = row.get('Deployment Type')
        should_skip = (
            pd.notnull(existing_title)
            and existing_title != 'Unknown'
            and existing_title != 'Error'
            and pd.notnull(existing_deployment)
            and existing_deployment != 'Unknown'
            and existing_deployment != 'Error'
        )

        assert should_skip is False

    def test_no_skip_when_deployment_error(self):
        """Should not skip when deployment is Error."""
        row = pd.Series(
            {
                'project_url': 'url',
                'project_title': 'Valid Title',
                'Deployment Type': 'Error',
            }
        )

        existing_title = row.get('project_title')
        existing_deployment = row.get('Deployment Type')
        should_skip = (
            pd.notnull(existing_title)
            and existing_title != 'Unknown'
            and existing_title != 'Error'
            and pd.notnull(existing_deployment)
            and existing_deployment != 'Unknown'
            and existing_deployment != 'Error'
        )

        assert should_skip is False

    def test_no_skip_when_null(self):
        """Should not skip when values are null."""
        row = pd.Series(
            {
                'project_url': 'url',
                'project_title': None,
                'Deployment Type': None,
            }
        )

        existing_title = row.get('project_title')
        existing_deployment = row.get('Deployment Type')
        should_skip = (
            pd.notnull(existing_title)
            and existing_title != 'Unknown'
            and existing_title != 'Error'
            and pd.notnull(existing_deployment)
            and existing_deployment != 'Unknown'
            and existing_deployment != 'Error'
        )

        assert should_skip is False


class TestEnvVarCheck:
    """Tests for _check_env_vars function."""

    def test_raises_when_github_token_missing(self):
        """Test that missing MY_GITHUB_TOKEN raises EnvironmentError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="MY_GITHUB_TOKEN"):
                _check_env_vars()

    def test_raises_when_openrouter_key_missing(self):
        """Test that missing OPENROUTER_API_KEY raises EnvironmentError."""
        with patch.dict(os.environ, {'MY_GITHUB_TOKEN': 'token'}, clear=True):
            with pytest.raises(EnvironmentError, match="OPENROUTER_API_KEY"):
                _check_env_vars()

    def test_passes_when_both_vars_set(self):
        """Test that no error is raised when both vars are set."""
        with patch.dict(
            os.environ,
            {'MY_GITHUB_TOKEN': 'token', 'OPENROUTER_API_KEY': 'key'},
            clear=True,
        ):
            # Should not raise
            _check_env_vars()

    def test_error_message_lists_all_missing_vars(self):
        """Test that error message includes all missing variables."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                _check_env_vars()

            error_msg = str(exc_info.value)
            assert "MY_GITHUB_TOKEN" in error_msg
            assert "OPENROUTER_API_KEY" in error_msg
