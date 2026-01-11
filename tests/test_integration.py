"""
Integration tests for the full pipeline.
Tests the complete flow from scraping to final CSV output with mocked external APIs.
"""

import os
import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pandas as pd
import pytest


class TestFullPipelineIntegration:
    """Integration tests that run the full pipeline with mocked APIs."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory structure."""
        return tmp_path

    @pytest.fixture
    def mock_github_responses(self):
        """Mock GitHub API responses for multiple repos."""

        def create_response(readme_content, files=None):
            if files is None:
                files = ['README.md', 'docker-compose.yml']

            return {
                'tree': [{'path': f, 'type': 'blob'} for f in files],
                'readme': base64.b64encode(readme_content.encode()).decode(),
            }

        return {
            'https://github.com/user1/taxi-pipeline': create_response(
                "# NYC Taxi Pipeline\nUses Airflow and BigQuery for batch processing."
            ),
            'https://github.com/user2/kafka-stream': create_response(
                "# Kafka Streaming\nReal-time data processing with Kafka and AWS Kinesis."
            ),
            'https://github.com/user3/ml-api': create_response(
                "# ML API\nFastAPI service for ML predictions on Azure."
            ),
        }

    @pytest.fixture
    def mock_openai_responses(self):
        """Mock OpenAI/LLM responses for classification and title generation."""
        return {
            'taxi': {
                'classification': "DEPLOYMENT: Batch\nDEPLOYMENT_REASON: Uses Airflow DAGs\nCLOUD: GCP\nCLOUD_REASON: Uses BigQuery",
                'summary': "A data pipeline for NYC taxi trip analysis using Airflow.",
                'titles': "1. NYC Taxi Fare Analytics\n2. Taxi Trip Data Pipeline\n3. Urban Transport Insights",
            },
            'kafka': {
                'classification': "DEPLOYMENT: Streaming\nDEPLOYMENT_REASON: Uses Kafka\nCLOUD: AWS\nCLOUD_REASON: Uses Kinesis",
                'summary': "Real-time streaming pipeline for event processing.",
                'titles': "1. Real-Time Event Processor\n2. Kafka Stream Analytics\n3. Live Data Pipeline",
            },
            'ml': {
                'classification': "DEPLOYMENT: Web Service\nDEPLOYMENT_REASON: Uses FastAPI\nCLOUD: Azure\nCLOUD_REASON: Uses Azure ML",
                'summary': "ML model serving API for predictions.",
                'titles': "1. ML Prediction Service\n2. Model Inference API\n3. AI Prediction Platform",
            },
        }

    @patch('utils.scraping_handler.requests.get')
    def test_scraping_step(self, mock_get, temp_data_dir):
        """Test the scraping step creates correct CSV."""
        from utils.scraping_handler import ScrapingHandler

        # Mock course page HTML
        html = """
        <html>
        <div class="list-group-item">
            <a href="https://github.com/user1/taxi-pipeline">Project 1</a>
        </div>
        <div class="list-group-item">
            <a href="https://github.com/user2/kafka-stream">Project 2</a>
        </div>
        <div class="list-group-item">
            <a href="https://github.com/user3/ml-api">Project 3</a>
        </div>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        handler = ScrapingHandler(
            url="https://courses.datatalks.club/de-zoomcamp-2024/projects",
            folder_path=str(temp_data_dir),
            course="dezoomcamp",
            year=2024,
        )
        filenames = handler.scrape_data()

        # Verify CSV was created
        csv_path = temp_data_dir / "dezoomcamp" / "2024" / filenames[0]
        assert csv_path.exists()

        df = pd.read_csv(csv_path)
        assert len(df) == 3
        assert 'project_url' in df.columns
        assert 'github.com/user1/taxi-pipeline' in df['project_url'].iloc[0]

    def test_combine_csvs_step(self, temp_data_dir):
        """Test the CSV combination step."""
        from src.combine_csvs import combine_files
        from utils.csv_handler import CSVHandler

        # Create test directory and CSVs
        course_dir = temp_data_dir / "dezoomcamp" / "2024"
        course_dir.mkdir(parents=True)

        # Create multiple scraped CSVs
        pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user1/repo1',
                    'https://github.com/user2/repo2',
                ]
            }
        ).to_csv(course_dir / "scraped_1.csv", index=False)

        pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user3/repo3',
                    'https://github.com/user1/repo1',
                ]  # duplicate
            }
        ).to_csv(course_dir / "scraped_2.csv", index=False)

        # Combine
        combined_df = combine_files(str(course_dir))
        assert len(combined_df) == 4  # Before dedup

        # Clean and deduplicate
        handler = CSVHandler(combined_df)
        handler.clean_and_deduplicate('project_url')
        assert len(handler.df) == 3  # After dedup

    @patch('utils.repo_analyzer.requests.get')
    @patch('utils.openai_api.OpenAI')
    def test_classification_step(self, mock_openai_class, mock_requests, temp_data_dir):
        """Test the classification step with mocked APIs."""
        from utils.openai_api import OpenAIAPI
        from utils.repo_analyzer import RepoAnalyzer
        from src.generate_titles_and_classify import process_single_project

        # Setup GitHub mock
        def github_mock(url, **kwargs):
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
                content = "# NYC Taxi Pipeline\nUses Airflow and BigQuery"
                response.json.return_value = {
                    'type': 'file',
                    'content': base64.b64encode(content.encode()).decode(),
                }
            else:
                response.ok = False
            return response

        mock_requests.side_effect = github_mock

        # Setup OpenAI mock
        mock_client = Mock()
        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            prompt = kwargs['messages'][0]['content']

            response = Mock()
            if 'DEPLOYMENT' in prompt:
                response.choices = [
                    Mock(
                        message=Mock(
                            content="DEPLOYMENT: Batch\nDEPLOYMENT_REASON: Uses Airflow\nCLOUD: GCP\nCLOUD_REASON: BigQuery"
                        )
                    )
                ]
            elif 'Summarize' in prompt:
                response.choices = [
                    Mock(
                        message=Mock(content="A data pipeline for taxi data analysis.")
                    )
                ]
            else:
                response.choices = [
                    Mock(
                        message=Mock(
                            content="1. NYC Taxi Analytics\n2. Taxi Data Pipeline"
                        )
                    )
                ]
            response.usage = Mock()
            return response

        mock_client.chat.completions.create = mock_create
        mock_openai_class.return_value = mock_client

        # Create test row
        row = pd.Series(
            {
                'project_url': 'https://github.com/user/taxi-pipeline',
                'project_title': None,
                'Deployment Type': None,
                'Reason': None,
                'Cloud': None,
            }
        )

        # Process
        repo_analyzer = RepoAnalyzer(github_token="test")
        openai_api = OpenAIAPI(api_key="test")

        args = (0, row, repo_analyzer, openai_api, ['Batch', 'Streaming'])
        index, result = process_single_project(args)

        # Verify results
        assert result['status'] == 'success'
        assert result['Deployment Type'] == 'Batch'
        assert result['Cloud'] == 'GCP'
        assert result['project_title'] is not None
        assert result['project_title'] != 'Unknown'

    @patch('utils.scraping_handler.requests.get')
    @patch('utils.repo_analyzer.requests.get')
    @patch('utils.openai_api.OpenAI')
    def test_full_pipeline_flow(
        self, mock_openai_class, mock_github, mock_scrape, temp_data_dir
    ):
        """Test the complete pipeline from scraping to final output."""
        from src.combine_csvs import combine_files
        from utils.openai_api import OpenAIAPI
        from utils.csv_handler import CSVHandler
        from utils.repo_analyzer import RepoAnalyzer
        from utils.scraping_handler import ScrapingHandler
        from src.generate_titles_and_classify import process_single_project

        # Step 1: Mock scraping
        scrape_html = """
        <html>
        <div class="list-group-item">
            <a href="https://github.com/user1/taxi-pipeline">Project 1</a>
        </div>
        <div class="list-group-item">
            <a href="https://github.com/user2/weather-data">Project 2</a>
        </div>
        </html>
        """
        mock_scrape_response = Mock()
        mock_scrape_response.content = scrape_html.encode()
        mock_scrape_response.raise_for_status = Mock()
        mock_scrape.return_value = mock_scrape_response

        handler = ScrapingHandler(
            url="https://courses.datatalks.club/test/projects",
            folder_path=str(temp_data_dir),
            course="testcourse",
            year=2024,
        )
        filenames = handler.scrape_data()

        # Step 2: Combine CSVs
        course_dir = temp_data_dir / "testcourse" / "2024"
        combined_df = combine_files(str(course_dir))

        csv_handler = CSVHandler(combined_df)
        csv_handler.clean_and_deduplicate('project_url')

        # Initialize columns
        for col in ['project_title', 'Deployment Type', 'Reason', 'Cloud']:
            csv_handler.df[col] = None

        # Step 3: Mock GitHub API for classification
        def github_mock(url, **kwargs):
            response = Mock()
            if 'git/trees' in url:
                response.ok = True
                response.json.return_value = {
                    'tree': [{'path': 'README.md', 'type': 'blob'}]
                }
            elif 'contents' in url:
                response.ok = True
                response.json.return_value = {
                    'type': 'file',
                    'content': base64.b64encode(b"# Test Project").decode(),
                }
            else:
                response.ok = False
            return response

        mock_github.side_effect = github_mock

        # Mock OpenAI
        mock_client = Mock()

        def mock_create(**kwargs):
            response = Mock()
            prompt = kwargs['messages'][0]['content']
            if 'DEPLOYMENT' in prompt:
                response.choices = [
                    Mock(
                        message=Mock(
                            content="DEPLOYMENT: Batch\nDEPLOYMENT_REASON: test\nCLOUD: GCP\nCLOUD_REASON: test"
                        )
                    )
                ]
            elif 'Summarize' in prompt:
                response.choices = [Mock(message=Mock(content="A test project."))]
            else:
                response.choices = [
                    Mock(message=Mock(content="1. Test Title\n2. Another Title"))
                ]
            response.usage = Mock()
            return response

        mock_client.chat.completions.create = mock_create
        mock_openai_class.return_value = mock_client

        # Step 4: Process each project
        repo_analyzer = RepoAnalyzer(github_token="test")
        openai_api = OpenAIAPI(api_key="test")

        for idx, row in csv_handler.df.iterrows():
            args = (idx, row, repo_analyzer, openai_api, ['Batch', 'Streaming'])
            index, result = process_single_project(args)

            csv_handler.df.at[index, 'project_title'] = result['project_title']
            csv_handler.df.at[index, 'Deployment Type'] = result['Deployment Type']
            csv_handler.df.at[index, 'Reason'] = result['Reason']
            csv_handler.df.at[index, 'Cloud'] = result['Cloud']

        # Step 5: Save final output
        output_path = course_dir / "data.csv"
        csv_handler.save(str(output_path))

        # Verify final output
        assert output_path.exists()
        final_df = pd.read_csv(output_path)

        assert len(final_df) == 2
        assert 'project_url' in final_df.columns
        assert 'project_title' in final_df.columns
        assert 'Deployment Type' in final_df.columns
        assert 'Cloud' in final_df.columns

        # All projects should be classified
        assert final_df['Deployment Type'].notna().all()
        assert final_df['Cloud'].notna().all()


class TestPipelineRunnerIntegration:
    """Integration tests for the PipelineRunner orchestrator."""

    @patch('src.pipeline_runner.ScrapingHandler')
    @patch('src.pipeline_runner.subprocess.run')
    @patch('src.pipeline_runner.CourseDiscovery')
    def test_pipeline_runner_single_course(
        self, mock_discovery_class, mock_subprocess, mock_scraping_class, tmp_path
    ):
        """Test PipelineRunner processes a single course."""
        from src.pipeline_runner import PipelineRunner

        # Mock discovery
        mock_discovery = Mock()
        mock_discovery.discover_courses.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'url': 'http://test.com/projects'}
        ]
        mock_discovery_class.return_value = mock_discovery

        # Mock scraping
        mock_scraper = Mock()
        mock_scraper.scrape_data.return_value = ['scraped.csv']
        mock_scraping_class.return_value = mock_scraper

        # Mock subprocess (for combine_csvs and generate_titles_and_classify)
        mock_subprocess.return_value = Mock(returncode=0)

        runner = PipelineRunner(data_path=str(tmp_path))
        result = runner.run(course='dezoomcamp', year=2024)

        assert result is True
        mock_scraper.scrape_data.assert_called_once()
        assert mock_subprocess.call_count == 2  # combine + classify

    @patch('src.pipeline_runner.CourseDiscovery')
    def test_pipeline_runner_discover(self, mock_discovery_class, tmp_path, capsys):
        """Test PipelineRunner discover mode."""
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.get_status.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'has_data': True},
            {'name': 'mlzoomcamp', 'year': 2024, 'has_data': False},
        ]
        mock_discovery_class.return_value = mock_discovery

        runner = PipelineRunner(data_path=str(tmp_path))
        runner.discover()

        captured = capsys.readouterr()
        assert 'dezoomcamp' in captured.out
        assert 'mlzoomcamp' in captured.out
        assert '✓' in captured.out  # Has data indicator

    @patch('src.pipeline_runner.ScrapingHandler')
    @patch('src.pipeline_runner.subprocess.run')
    @patch('src.pipeline_runner.CourseDiscovery')
    def test_pipeline_runner_handles_scraping_error(
        self, mock_discovery_class, mock_subprocess, mock_scraping_class, tmp_path
    ):
        """Test PipelineRunner handles scraping errors gracefully."""
        from src.pipeline_runner import PipelineRunner
        from utils.scraping_handler import ScrapingError

        mock_discovery = Mock()
        mock_discovery.discover_courses.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'url': 'http://test.com'}
        ]
        mock_discovery_class.return_value = mock_discovery

        mock_scraper = Mock()
        mock_scraper.scrape_data.side_effect = ScrapingError("No projects found")
        mock_scraping_class.return_value = mock_scraper

        runner = PipelineRunner(data_path=str(tmp_path))
        result = runner.run(course='dezoomcamp', year=2024)

        assert result is False
        mock_subprocess.assert_not_called()  # Should not proceed to next steps


class TestCourseDiscoveryIntegration:
    """Integration tests for course discovery."""

    @patch('utils.course_discovery.requests.get')
    def test_discovers_multiple_courses(self, mock_get):
        """Test discovering multiple courses from the website."""
        from utils.course_discovery import CourseDiscovery

        html = """
        <html>
        <h3>Finished courses</h3>
        <ul>
            <li><a href="/de-zoomcamp-2024">DE Zoomcamp 2024</a></li>
            <li><a href="/de-zoomcamp-2023">DE Zoomcamp 2023</a></li>
            <li><a href="/ml-zoomcamp-2024">ML Zoomcamp 2024</a></li>
            <li><a href="/mlops-zoomcamp-2024">MLOps Zoomcamp 2024</a></li>
            <li><a href="/llm-zoomcamp-2024">LLM Zoomcamp 2024</a></li>
        </ul>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        assert len(courses) == 5
        course_names = [c['name'] for c in courses]
        assert 'dezoomcamp' in course_names
        assert 'mlzoomcamp' in course_names
        assert 'mlopszoomcamp' in course_names
        assert 'llmzoomcamp' in course_names

    @patch('utils.course_discovery.requests.get')
    def test_get_missing_courses(self, mock_get, tmp_path):
        """Test identifying missing courses."""
        from utils.course_discovery import CourseDiscovery

        html = """
        <html>
        <h3>Finished courses</h3>
        <li><a href="/de-zoomcamp-2024">DE 2024</a></li>
        <li><a href="/de-zoomcamp-2023">DE 2023</a></li>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Create data for 2023 only
        data_dir = tmp_path / "dezoomcamp" / "2023"
        data_dir.mkdir(parents=True)
        (data_dir / "data.csv").write_text("project_url\nhttp://test.com")

        discovery = CourseDiscovery(data_path=str(tmp_path))
        missing = discovery.get_missing_courses()

        assert len(missing) == 1
        assert missing[0]['year'] == 2024


class TestDataIntegrity:
    """Tests for data integrity throughout the pipeline."""

    def test_urls_preserved_through_pipeline(self, tmp_path):
        """Test that project URLs are preserved correctly."""
        from utils.csv_handler import CSVHandler

        original_urls = [
            'https://github.com/user1/repo1',
            'https://github.com/user2/repo2',
            'https://github.com/user3/repo3',
        ]

        df = pd.DataFrame({'project_url': original_urls})
        handler = CSVHandler(df)
        handler.clean_and_deduplicate('project_url')

        output_path = tmp_path / "output.csv"
        handler.save(str(output_path))

        loaded = pd.read_csv(output_path)
        assert list(loaded['project_url']) == original_urls

    def test_special_characters_in_titles(self, tmp_path):
        """Test that special characters in titles are handled."""
        from utils.csv_handler import CSVHandler

        df = pd.DataFrame(
            {
                'project_url': ['url1', 'url2'],
                'project_title': ['São Paulo Analytics', 'Kraków Data Pipeline'],
            }
        )

        handler = CSVHandler(df)
        output_path = tmp_path / "output.csv"
        handler.save(str(output_path))

        loaded = pd.read_csv(output_path)
        assert 'São Paulo' in loaded['project_title'].iloc[0]
        assert 'Kraków' in loaded['project_title'].iloc[1]

    def test_deployment_types_are_valid(self):
        """Test that only valid deployment types are used."""
        from src.config import COURSE_DEPLOYMENT_TYPES

        valid_types = {'Batch', 'Streaming', 'Web Service'}

        for course, types in COURSE_DEPLOYMENT_TYPES.items():
            for t in types:
                assert t in valid_types, f"Invalid type {t} for course {course}"


class TestGenerateTitlesAndClassifyMain:
    """Integration tests for generate_titles_and_classify main function."""

    @patch('src.generate_titles_and_classify.RepoAnalyzer')
    @patch('src.generate_titles_and_classify.OpenAIAPI')
    @patch('src.generate_titles_and_classify.CSVHandler')
    @patch('src.generate_titles_and_classify.get_config')
    def test_main_function_flow(
        self,
        mock_config,
        mock_csv_class,
        mock_openai_class,
        mock_analyzer_class,
        tmp_path,
        monkeypatch,
    ):
        """Test the main function orchestration."""
        # Set required env vars
        monkeypatch.setenv('MY_GITHUB_TOKEN', 'test_token')
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test_key')

        from src.generate_titles_and_classify import main

        # Setup config
        csv_path = tmp_path / "input.csv"
        output_path = tmp_path / "output.csv"

        # Create test CSV
        pd.DataFrame(
            {
                'project_url': [
                    'https://github.com/user/repo1',
                    'https://github.com/user/repo2',
                ],
                'project_title': [None, None],
                'Deployment Type': [None, None],
                'Reason': [None, None],
                'Cloud': [None, None],
            }
        ).to_csv(csv_path, index=False)

        mock_config.return_value = {
            'cleaned_csv_path': str(csv_path),
            'deploy_csv_path': str(output_path),
            'max_workers': 1,
            'limit': 0,
            'valid_deployment_types': ['Batch', 'Streaming'],
            'course': 'testcourse',
        }

        # Setup CSV handler mock
        mock_handler = Mock()
        mock_handler.df = pd.DataFrame(
            {
                'project_url': ['https://github.com/user/repo1'],
                'project_title': [None],
                'Deployment Type': [None],
                'Reason': [None],
                'Cloud': [None],
            }
        )
        mock_csv_class.return_value = mock_handler

        # Setup analyzer mock
        mock_analyzer = Mock()
        mock_analyzer.analyze_repo.return_value = {'files': {'README.md': '# Test'}}
        mock_analyzer_class.return_value = mock_analyzer

        # Setup OpenAI mock
        mock_openai = Mock()
        mock_openai.classify_deployment_and_cloud.return_value = {
            'deployment_type': 'Batch',
            'deployment_reason': 'test',
            'cloud_provider': 'GCP',
        }
        mock_openai.generate_summary.return_value = "A test project"
        mock_openai.generate_multiple_titles.return_value = ['Test Title']
        mock_openai.evaluate_and_revise_titles.return_value = ('feedback', 'Best Title')
        mock_openai_class.return_value = mock_openai

        # Run main
        main()

        # Verify save was called
        mock_handler.save.assert_called_once()

    @patch('src.generate_titles_and_classify.get_config')
    def test_main_with_limit(self, mock_config, tmp_path, monkeypatch):
        """Test main function respects limit parameter."""
        # Set required env vars
        monkeypatch.setenv('MY_GITHUB_TOKEN', 'test_token')
        monkeypatch.setenv('OPENROUTER_API_KEY', 'test_key')

        from utils.csv_handler import CSVHandler
        from src.generate_titles_and_classify import main

        # Create test CSV with 5 rows
        csv_path = tmp_path / "input.csv"
        output_path = tmp_path / "output.csv"

        pd.DataFrame(
            {'project_url': [f'https://github.com/user/repo{i}' for i in range(5)]}
        ).to_csv(csv_path, index=False)

        mock_config.return_value = {
            'cleaned_csv_path': str(csv_path),
            'deploy_csv_path': str(output_path),
            'max_workers': 1,
            'limit': 2,  # Only process 2
            'valid_deployment_types': ['Batch'],
            'course': 'test',
        }

        # The function will fail on API calls, but we can verify limit is applied
        with patch('src.generate_titles_and_classify.RepoAnalyzer') as mock_analyzer:
            with patch('src.generate_titles_and_classify.OpenAIAPI') as mock_openai:
                mock_analyzer_instance = Mock()
                mock_analyzer_instance.analyze_repo.return_value = {'files': {}}
                mock_analyzer.return_value = mock_analyzer_instance

                mock_openai_instance = Mock()
                mock_openai.return_value = mock_openai_instance

                main()

                # Should only have called analyze_repo twice (limit=2)
                assert mock_analyzer_instance.analyze_repo.call_count == 2
