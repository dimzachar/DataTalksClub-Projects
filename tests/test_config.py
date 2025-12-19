"""Unit tests for config module."""

import sys
from unittest.mock import patch

import pytest


class TestCourseDeploymentTypes:
    """Tests for course-specific deployment types."""

    def test_dezoomcamp_types(self):
        from src.config import COURSE_DEPLOYMENT_TYPES

        assert 'dezoomcamp' in COURSE_DEPLOYMENT_TYPES
        types = COURSE_DEPLOYMENT_TYPES['dezoomcamp']
        assert 'Batch' in types
        assert 'Streaming' in types
        assert 'Web Service' not in types

    def test_mlzoomcamp_types(self):
        from src.config import COURSE_DEPLOYMENT_TYPES

        assert 'mlzoomcamp' in COURSE_DEPLOYMENT_TYPES
        types = COURSE_DEPLOYMENT_TYPES['mlzoomcamp']
        assert 'Batch' in types
        assert 'Web Service' in types

    def test_mlopszoomcamp_types(self):
        from src.config import COURSE_DEPLOYMENT_TYPES

        assert 'mlopszoomcamp' in COURSE_DEPLOYMENT_TYPES
        types = COURSE_DEPLOYMENT_TYPES['mlopszoomcamp']
        assert 'Batch' in types
        assert 'Web Service' in types

    def test_llmzoomcamp_types(self):
        from src.config import COURSE_DEPLOYMENT_TYPES

        assert 'llmzoomcamp' in COURSE_DEPLOYMENT_TYPES
        types = COURSE_DEPLOYMENT_TYPES['llmzoomcamp']
        assert 'Batch' in types
        assert 'Web Service' in types


class TestGetConfig:
    """Tests for get_config function."""

    @patch('sys.argv', ['test', '--course', 'dezoomcamp', '--year', '2025'])
    def test_basic_config(self):
        from src.config import get_config

        config = get_config()

        assert config['course'] == 'dezoomcamp'
        assert config['year'] == 2025
        assert config['base_path'] == 'Data'
        assert 'valid_deployment_types' in config

    @patch('sys.argv', ['test', '--course', 'dezoomcamp', '--year', '2025'])
    def test_dezoomcamp_valid_types(self):
        from src.config import get_config

        config = get_config()

        assert config['valid_deployment_types'] == ['Batch', 'Streaming']

    @patch('sys.argv', ['test', '--course', 'mlzoomcamp', '--year', '2024'])
    def test_mlzoomcamp_valid_types(self):
        from src.config import get_config

        config = get_config()

        assert 'Batch' in config['valid_deployment_types']
        assert 'Web Service' in config['valid_deployment_types']

    @patch('sys.argv', ['test', '--course', 'unknown_course', '--year', '2024'])
    def test_unknown_course_gets_all_types(self):
        from src.config import get_config

        config = get_config()

        # Unknown courses should get all types as default
        assert 'Batch' in config['valid_deployment_types']
        assert 'Streaming' in config['valid_deployment_types']
        assert 'Web Service' in config['valid_deployment_types']

    @patch(
        'sys.argv',
        ['test', '--course', 'dezoomcamp', '--year', '2025', '--limit', '10'],
    )
    def test_limit_option(self):
        from src.config import get_config

        config = get_config()

        assert config['limit'] == 10

    @patch(
        'sys.argv',
        ['test', '--course', 'dezoomcamp', '--year', '2025', '--workers', '8'],
    )
    def test_workers_option(self):
        from src.config import get_config

        config = get_config()

        assert config['max_workers'] == 8

    @patch('sys.argv', ['test', '--course', 'dezoomcamp', '--year', '2025'])
    def test_paths_generated_correctly(self):
        from src.config import get_config

        config = get_config()

        assert 'dezoomcamp' in config['subdirectory']
        assert '2025' in config['subdirectory']
        assert config['cleaned_csv_path'].endswith('.csv')
        assert config['deploy_csv_path'].endswith('data.csv')
