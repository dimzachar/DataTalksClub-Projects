"""End-to-end tests for the complete pipeline."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pandas as pd
import pytest


class TestFullPipelineE2E:
    """End-to-end tests simulating the complete pipeline flow."""

    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables."""
        monkeypatch.setenv('MY_GITHUB_TOKEN', 'test_token')
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test_key')

    @pytest.fixture
    def sample_scraped_data(self, tmp_path):
        """Create sample scraped CSV data."""
        course_dir = tmp_path / "dezoomcamp" / "2024"
        course_dir.mkdir(parents=True)

        df = pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user1/taxi-pipeline',
                    'https://github.com/user2/weather-data',
                    'https://github.com/user3/stock-analysis',
                ]
            }
        )
        csv_path = course_dir / "scraped_data_dezoomcamp_2024.csv"
        df.to_csv(csv_path, index=False)

        return tmp_path, course_dir

    def test_combine_csvs_step(self, sample_scraped_data):
        """Test the CSV combination step."""
        tmp_path, course_dir = sample_scraped_data

        from src.combine_csvs import combine_files
        from utils.csv_handler import CSVHandler

        # Combine files
        combined_df = combine_files(str(course_dir))

        assert len(combined_df) == 3
        assert 'project_url' in combined_df.columns

        # Clean and deduplicate
        handler = CSVHandler(combined_df)
        handler.clean_and_deduplicate('project_url')

        assert len(handler.df) == 3

    @patch('utils.repo_analyzer.requests.get')
    @patch('utils.openai_api.OpenAI')
    def test_classification_step(
        self, mock_openai_class, mock_requests, sample_scraped_data, mock_env
    ):
        """Test the classification step with mocked APIs."""
        import base64

        tmp_path, course_dir = sample_scraped_data

        # Mock GitHub API responses
        def mock_get(url, **kwargs):
            response = Mock()
            if 'git/trees' in url:
                response.ok = True
                response.json.return_value = {
                    'tree': [
                        {'path': 'README.md', 'type': 'blob'},
                        {'path': 'docker-compose.yml', 'type': 'blob'},
                    ]
                }
            elif 'contents' in url:
                response.ok = True
                content = "# Test Project\nUses Airflow and BigQuery"
                response.json.return_value = {
                    'type': 'file',
                    'content': base64.b64encode(content.encode()).decode(),
                }
            else:
                response.ok = False
            return response

        mock_requests.side_effect = mock_get

        # Mock OpenAI responses
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content="DEPLOYMENT: Batch\nDEPLOYMENT_REASON: Uses Airflow\nCLOUD: GCP\nCLOUD_REASON: Uses BigQuery"
                )
            )
        ]
        mock_response.usage = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        from utils.openai_api import OpenAIAPI
        from utils.repo_analyzer import RepoAnalyzer

        # Test repo analyzer
        analyzer = RepoAnalyzer(github_token="test")
        result = analyzer.analyze_repo("https://github.com/user/repo")

        assert result['owner'] == 'user'
        assert result['repo'] == 'repo'

        # Test classification
        api = OpenAIAPI(api_key="test")
        classification = api.classify_deployment_and_cloud(
            "https://github.com/user/repo",
            {'README.md': '# Test\nUses Airflow'},
            valid_deployment_types=['Batch', 'Streaming'],
        )

        assert classification['deployment_type'] == 'Batch'
        assert classification['cloud_provider'] == 'GCP'

    def test_csv_handler_full_workflow(self, tmp_path):
        """Test CSVHandler through full workflow."""
        from utils.csv_handler import CSVHandler

        # Create input
        input_df = pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user/repo1',
                    'https://github.com/user/repo1',  # duplicate
                    'https://github.com/user/repo2',
                ],
                'extra_col': ['a', 'b', 'c'],
            }
        )
        input_path = tmp_path / "input.csv"
        input_df.to_csv(input_path, index=False)

        # Process
        handler = CSVHandler(str(input_path))
        handler.clean_and_deduplicate('project_url')

        # Add titles
        handler.update_titles(['Title 1', 'Title 2'])

        # Add deployment info
        handler.df['Deployment Type'] = ['Batch', 'Streaming']
        handler.df['Cloud'] = ['GCP', 'AWS']

        # Save
        output_path = tmp_path / "output.csv"
        handler.save(str(output_path))

        # Verify
        result = pd.read_csv(output_path)
        assert len(result) == 2
        assert 'project_title' in result.columns
        assert 'Deployment Type' in result.columns
        assert 'Cloud' in result.columns
        assert 'extra_col' not in result.columns


class TestPipelineDataFlow:
    """Tests for data flow through pipeline stages."""

    def test_scraped_to_combined(self, tmp_path):
        """Test data flows correctly from scraping to combination."""
        from src.combine_csvs import combine_files
        from utils.csv_handler import CSVHandler

        # Simulate multiple scraped files
        course_dir = tmp_path / "course" / "2024"
        course_dir.mkdir(parents=True)

        pd.DataFrame({'project_url': ['url1', 'url2']}).to_csv(
            course_dir / "scraped_1.csv", index=False
        )
        pd.DataFrame({'project_url': ['url3', 'url4']}).to_csv(
            course_dir / "scraped_2.csv", index=False
        )

        # Combine
        combined = combine_files(str(course_dir))
        assert len(combined) == 4

        # Clean
        handler = CSVHandler(combined)
        handler.clean_and_deduplicate('project_url')
        assert len(handler.df) == 4

    def test_combined_to_classified(self, tmp_path):
        """Test data flows from combined CSV to classification."""
        from utils.csv_handler import CSVHandler

        # Create combined CSV
        df = pd.DataFrame({'project_url': ['url1', 'url2', 'url3']})
        csv_path = tmp_path / "combined.csv"
        df.to_csv(csv_path, index=False)

        # Load and add columns
        handler = CSVHandler(str(csv_path))

        # Simulate classification results
        handler.df['project_title'] = ['Title 1', 'Title 2', 'Title 3']
        handler.df['Deployment Type'] = ['Batch', 'Streaming', 'Web Service']
        handler.df['Reason'] = ['Airflow', 'Kafka', 'FastAPI']
        handler.df['Cloud'] = ['GCP', 'AWS', 'Azure']

        # Save final
        output_path = tmp_path / "data.csv"
        handler.save(str(output_path))

        # Verify final output
        result = pd.read_csv(output_path)
        assert len(result) == 3
        assert all(
            col in result.columns
            for col in [
                'project_url',
                'project_title',
                'Deployment Type',
                'Reason',
                'Cloud',
            ]
        )


class TestErrorHandling:
    """Tests for error handling throughout the pipeline."""

    def test_handles_empty_csv(self, tmp_path):
        """Test pipeline handles empty CSV gracefully."""
        from utils.csv_handler import CSVHandler

        # Create empty CSV with headers
        df = pd.DataFrame(columns=['project_url'])
        csv_path = tmp_path / "empty.csv"
        df.to_csv(csv_path, index=False)

        handler = CSVHandler(str(csv_path))
        handler.clean_and_deduplicate('project_url')

        assert len(handler.df) == 0

    def test_handles_malformed_urls(self, tmp_path):
        """Test pipeline handles malformed URLs."""
        from utils.repo_analyzer import RepoAnalyzer

        analyzer = RepoAnalyzer()

        # Test various malformed URLs
        result = analyzer.parse_github_url("not-a-url")
        # Should not crash, may return None values

        result = analyzer.parse_github_url("")
        # Should handle empty string

        result = analyzer.parse_github_url("https://gitlab.com/user/repo")
        # Non-GitHub URL

    def test_handles_missing_columns(self, tmp_path):
        """Test pipeline handles missing columns."""
        from utils.csv_handler import CSVHandler

        df = pd.DataFrame({'other_column': ['value']})
        csv_path = tmp_path / "missing_col.csv"
        df.to_csv(csv_path, index=False)

        handler = CSVHandler(str(csv_path))
        # Should not crash, just warn
        handler.clean_and_deduplicate('project_url')


class TestDeploymentTypeValidation:
    """Tests for deployment type validation per course."""

    def test_dezoomcamp_valid_types(self):
        """DE Zoomcamp should only allow Batch and Streaming."""
        from src.config import COURSE_DEPLOYMENT_TYPES

        types = COURSE_DEPLOYMENT_TYPES['dezoomcamp']
        assert 'Batch' in types
        assert 'Streaming' in types
        assert 'Web Service' not in types

    def test_mlzoomcamp_valid_types(self):
        """ML Zoomcamp should allow Web Service."""
        from src.config import COURSE_DEPLOYMENT_TYPES

        types = COURSE_DEPLOYMENT_TYPES['mlzoomcamp']
        assert 'Web Service' in types

    @patch('utils.openai_api.OpenAI')
    def test_classification_respects_valid_types(self, mock_openai_class):
        """Classification should use course-specific valid types."""
        from utils.openai_api import OpenAIAPI

        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content="DEPLOYMENT: Batch\nDEPLOYMENT_REASON: test\nCLOUD: GCP\nCLOUD_REASON: test"
                )
            )
        ]
        mock_response.usage = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        api = OpenAIAPI(api_key="test")

        # Call with restricted types
        result = api.classify_deployment_and_cloud(
            "https://github.com/user/repo",
            {'README.md': '# Test'},
            valid_deployment_types=['Batch', 'Streaming'],  # No Web Service
        )

        # Verify the prompt included the valid types
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]['messages'][0]['content']
        assert 'Batch' in prompt
        assert 'Streaming' in prompt


class TestOutputFormat:
    """Tests for final output format."""

    def test_final_csv_has_required_columns(self, tmp_path):
        """Final CSV should have all required columns."""
        from utils.csv_handler import CSVHandler

        df = pd.DataFrame(
            {
                'project_url': ['url1'],
                'project_title': ['Title'],
                'Deployment Type': ['Batch'],
                'Reason': ['Uses Airflow'],
                'Cloud': ['GCP'],
            }
        )

        handler = CSVHandler(df)
        output_path = tmp_path / "data.csv"
        handler.save(str(output_path))

        result = pd.read_csv(output_path)
        required_cols = [
            'project_url',
            'project_title',
            'Deployment Type',
            'Reason',
            'Cloud',
        ]

        for col in required_cols:
            assert col in result.columns

    def test_no_index_in_output(self, tmp_path):
        """Output CSV should not have index column."""
        from utils.csv_handler import CSVHandler

        df = pd.DataFrame({'project_url': ['url1']})
        handler = CSVHandler(df)

        output_path = tmp_path / "output.csv"
        handler.save(str(output_path))

        result = pd.read_csv(output_path)
        assert 'Unnamed: 0' not in result.columns
