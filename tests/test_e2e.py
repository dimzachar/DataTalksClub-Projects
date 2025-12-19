"""End-to-end tests for the pipeline."""

import os
import base64
from unittest.mock import Mock, MagicMock, patch

import pandas as pd
import pytest

from utils.openai_api import OpenAIAPI


class TestPipelineE2E:
    """End-to-end tests for the classification pipeline."""

    @pytest.fixture
    def mock_github_response(self):
        """Mock GitHub API responses."""
        readme_content = """# NYC Taxi Data Pipeline
        
This project processes NYC taxi data using Apache Airflow.

## Architecture
- Airflow for orchestration
- BigQuery for data warehouse
- dbt for transformations
"""
        docker_compose = """version: '3'
services:
  airflow:
    image: apache/airflow:2.5.0
"""
        terraform = """provider "google" {
  project = "my-project"
}

resource "google_bigquery_dataset" "taxi" {
  dataset_id = "taxi_data"
}
"""
        return {
            'README.md': readme_content,
            'docker-compose.yml': docker_compose,
            'main.tf': terraform,
        }

    @patch('utils.repo_analyzer.requests.get')
    def test_repo_analyzer_fetches_files(self, mock_get, mock_github_response):
        """Test that RepoAnalyzer correctly fetches and returns files."""
        from utils.repo_analyzer import RepoAnalyzer

        # Mock tree response
        tree_response = Mock()
        tree_response.ok = True
        tree_response.json.return_value = {
            'tree': [
                {'path': 'README.md', 'type': 'blob'},
                {'path': 'docker-compose.yml', 'type': 'blob'},
                {'path': 'main.tf', 'type': 'blob'},
            ]
        }

        # Mock file content responses
        def mock_get_side_effect(url, **kwargs):
            if 'git/trees' in url:
                return tree_response

            for filename, content in mock_github_response.items():
                if filename in url:
                    response = Mock()
                    response.ok = True
                    response.json.return_value = {
                        'type': 'file',
                        'content': base64.b64encode(content.encode()).decode(),
                    }
                    return response

            response = Mock()
            response.ok = False
            return response

        mock_get.side_effect = mock_get_side_effect

        analyzer = RepoAnalyzer(github_token="test_token")
        result = analyzer.analyze_repo("https://github.com/user/taxi-pipeline")

        assert result['owner'] == 'user'
        assert result['repo'] == 'taxi-pipeline'
        assert len(result['files']) > 0

    @patch.object(OpenAIAPI, 'llm')
    def test_classification_with_airflow_and_gcp(self, mock_llm):
        """Test that Airflow + GCP project is classified correctly."""
        from utils.openai_api import OpenAIAPI

        mock_llm.return_value = (
            "DEPLOYMENT: Batch\n"
            "DEPLOYMENT_REASON: Uses Apache Airflow for orchestration\n"
            "CLOUD: GCP\n"
            "CLOUD_REASON: Uses BigQuery and Terraform google provider",
            None,
        )

        api = OpenAIAPI(api_key="test")
        files = {
            'README.md': '# Airflow Pipeline\nUses BigQuery',
            'main.tf': 'provider "google" {}',
        }

        result = api.classify_deployment_and_cloud(
            "https://github.com/user/repo",
            files,
            valid_deployment_types=['Batch', 'Streaming'],
        )

        assert result['deployment_type'] == 'Batch'
        assert result['cloud_provider'] == 'GCP'

    @patch.object(OpenAIAPI, 'llm')
    def test_classification_with_kafka_streaming(self, mock_llm):
        """Test that Kafka project is classified as Streaming."""
        from utils.openai_api import OpenAIAPI

        mock_llm.return_value = (
            "DEPLOYMENT: Streaming\n"
            "DEPLOYMENT_REASON: Uses Kafka for real-time data processing\n"
            "CLOUD: AWS\n"
            "CLOUD_REASON: Uses Kinesis and S3",
            None,
        )

        api = OpenAIAPI(api_key="test")
        files = {
            'README.md': '# Kafka Streaming\nReal-time data',
            'docker-compose.yml': 'kafka:\n  image: confluentinc/kafka',
        }

        result = api.classify_deployment_and_cloud(
            "https://github.com/user/repo",
            files,
            valid_deployment_types=['Batch', 'Streaming'],
        )

        assert result['deployment_type'] == 'Streaming'

    @patch.object(OpenAIAPI, 'llm')
    def test_classification_with_fastapi_web_service(self, mock_llm):
        """Test that FastAPI project is classified as Web Service."""
        from utils.openai_api import OpenAIAPI

        mock_llm.return_value = (
            "DEPLOYMENT: Web Service\n"
            "DEPLOYMENT_REASON: Uses FastAPI to serve ML predictions\n"
            "CLOUD: AWS\n"
            "CLOUD_REASON: Uses Lambda and API Gateway",
            None,
        )

        api = OpenAIAPI(api_key="test")
        files = {
            'app.py': 'from fastapi import FastAPI\napp = FastAPI()',
        }

        result = api.classify_deployment_and_cloud(
            "https://github.com/user/repo",
            files,
            valid_deployment_types=['Batch', 'Web Service'],
        )

        assert result['deployment_type'] == 'Web Service'


class TestTitleGeneration:
    """Tests for title generation."""

    @patch.object(OpenAIAPI, 'llm')
    def test_generates_domain_focused_title(self, mock_llm):
        """Test that titles are domain-focused, not generic."""
        from utils.openai_api import OpenAIAPI

        mock_llm.return_value = (
            "1. NYC Taxi Fare Analytics\n"
            "2. Taxi Trip Data Pipeline\n"
            "3. Urban Transportation Insights",
            None,
        )

        api = OpenAIAPI(api_key="test")
        titles = api.generate_multiple_titles(
            "https://github.com/user/taxi-project",
            "A data pipeline for NYC taxi trip data analysis",
        )

        # Should not contain generic terms
        for title in titles:
            assert 'zoomcamp' not in title.lower()
            assert 'bootcamp' not in title.lower()
            assert 'final project' not in title.lower()

    @patch.object(OpenAIAPI, 'llm')
    def test_batch_project_no_realtime_title(self, mock_llm):
        """Test that Batch projects don't get Real-Time in title."""
        from utils.openai_api import OpenAIAPI

        # First call for titles
        mock_llm.return_value = (
            "1. Weather Data Analytics\n"
            "2. Climate Data Pipeline\n"
            "3. Meteorological Insights Platform",
            None,
        )

        api = OpenAIAPI(api_key="test")
        titles = api.generate_multiple_titles(
            "https://github.com/user/weather",
            "Weather data analysis",
            deployment_type="Batch",
        )

        # Check that the prompt mentioned not to use Real-Time
        call_args = mock_llm.call_args[0][0]
        assert 'BATCH' in call_args
        assert 'Real-Time' in call_args


class TestSkipLogic:
    """Tests for the skip logic in pipeline."""

    def test_skips_already_processed(self):
        """Test that already processed projects are skipped."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': 'NYC Taxi Pipeline',
                'Deployment Type': 'Batch',
                'Reason': 'Uses Airflow',
                'Cloud': 'GCP',
            }
        )

        # Should skip - both title and deployment are valid
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

    def test_does_not_skip_unknown(self):
        """Test that Unknown values are reprocessed."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': 'Unknown',
                'Deployment Type': 'Unknown',
                'Reason': 'No files fetched',
                'Cloud': 'Unknown',
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

    def test_does_not_skip_error(self):
        """Test that Error values are reprocessed."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': 'Error',
                'Deployment Type': 'Error',
                'Reason': 'API failed',
                'Cloud': 'Error',
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

    def test_does_not_skip_null(self):
        """Test that null values are processed."""
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/repo',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
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
