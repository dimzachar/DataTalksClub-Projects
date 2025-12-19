"""Unit tests for pipeline_runner module."""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest


class TestPipelineRunnerInit:
    """Tests for PipelineRunner initialization."""

    def test_default_data_path(self):
        from src.pipeline_runner import PipelineRunner

        runner = PipelineRunner()
        assert runner.data_path == Path("Data")

    def test_custom_data_path(self):
        from src.pipeline_runner import PipelineRunner

        runner = PipelineRunner(data_path="/custom/path")
        assert runner.data_path == Path("/custom/path")

    def test_limit_parameter(self):
        from src.pipeline_runner import PipelineRunner

        runner = PipelineRunner(limit=10)
        assert runner.limit == 10


class TestPipelineRunnerDiscover:
    """Tests for discover method."""

    @patch('src.pipeline_runner.CourseDiscovery')
    def test_discover_prints_status(self, mock_discovery_class, capsys):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.get_status.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'has_data': True},
            {'name': 'mlzoomcamp', 'year': 2024, 'has_data': False},
        ]
        mock_discovery_class.return_value = mock_discovery

        runner = PipelineRunner()
        runner.discover()

        captured = capsys.readouterr()
        assert 'dezoomcamp' in captured.out
        assert 'mlzoomcamp' in captured.out

    @patch('src.pipeline_runner.CourseDiscovery')
    def test_discover_handles_empty(self, mock_discovery_class, capsys):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.get_status.return_value = []
        mock_discovery_class.return_value = mock_discovery

        runner = PipelineRunner()
        runner.discover()

        captured = capsys.readouterr()
        assert 'No courses found' in captured.out


class TestPipelineRunnerRun:
    """Tests for run method."""

    @patch('src.pipeline_runner.CourseDiscovery')
    @patch.object(
        __import__('src.pipeline_runner', fromlist=['PipelineRunner']).PipelineRunner,
        '_process_course',
    )
    def test_run_processes_missing_courses(self, mock_process, mock_discovery_class):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.get_missing_courses.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'url': 'url1'},
        ]
        mock_discovery_class.return_value = mock_discovery
        mock_process.return_value = True

        runner = PipelineRunner()
        result = runner.run()

        assert result is True
        mock_process.assert_called_once()

    @patch('src.pipeline_runner.CourseDiscovery')
    def test_run_returns_true_when_nothing_to_process(
        self, mock_discovery_class, capsys
    ):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.get_missing_courses.return_value = []
        mock_discovery_class.return_value = mock_discovery

        runner = PipelineRunner()
        result = runner.run()

        assert result is True
        captured = capsys.readouterr()
        assert 'up to date' in captured.out

    @patch('src.pipeline_runner.CourseDiscovery')
    @patch.object(
        __import__('src.pipeline_runner', fromlist=['PipelineRunner']).PipelineRunner,
        '_process_course',
    )
    def test_run_force_all(self, mock_process, mock_discovery_class):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.discover_courses.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'url': 'url1'},
            {'name': 'dezoomcamp', 'year': 2023, 'url': 'url2'},
        ]
        mock_discovery_class.return_value = mock_discovery
        mock_process.return_value = True

        runner = PipelineRunner()
        result = runner.run(force_all=True)

        assert mock_process.call_count == 2

    @patch('src.pipeline_runner.CourseDiscovery')
    @patch.object(
        __import__('src.pipeline_runner', fromlist=['PipelineRunner']).PipelineRunner,
        '_process_course',
    )
    def test_run_specific_course(self, mock_process, mock_discovery_class):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.discover_courses.return_value = [
            {'name': 'dezoomcamp', 'year': 2024, 'url': 'url1'},
            {'name': 'mlzoomcamp', 'year': 2024, 'url': 'url2'},
        ]
        mock_discovery_class.return_value = mock_discovery
        mock_process.return_value = True

        runner = PipelineRunner()
        result = runner.run(course='dezoomcamp', year=2024)

        mock_process.assert_called_once()
        call_args = mock_process.call_args[0][0]
        assert call_args['name'] == 'dezoomcamp'

    @patch('src.pipeline_runner.CourseDiscovery')
    def test_run_course_not_found(self, mock_discovery_class, capsys):
        from src.pipeline_runner import PipelineRunner

        mock_discovery = Mock()
        mock_discovery.discover_courses.return_value = []
        mock_discovery_class.return_value = mock_discovery

        runner = PipelineRunner()
        result = runner.run(course='nonexistent', year=2024)

        assert result is False
        captured = capsys.readouterr()
        assert 'not found' in captured.out


class TestProcessCourse:
    """Tests for _process_course method."""

    @patch('src.pipeline_runner.ScrapingHandler')
    @patch.object(
        __import__('src.pipeline_runner', fromlist=['PipelineRunner']).PipelineRunner,
        '_run_step',
    )
    def test_process_course_success(self, mock_run_step, mock_scraping_class, tmp_path):
        from src.pipeline_runner import PipelineRunner

        mock_scraper = Mock()
        mock_scraper.scrape_data.return_value = ['file.csv']
        mock_scraping_class.return_value = mock_scraper

        runner = PipelineRunner(data_path=str(tmp_path))
        course = {'name': 'dezoomcamp', 'year': 2024, 'url': 'http://example.com'}

        result = runner._process_course(course)

        assert result is True
        assert (
            mock_run_step.call_count == 2
        )  # combine_csvs and generate_titles_and_classify

    @patch('src.pipeline_runner.ScrapingHandler')
    def test_process_course_scraping_error(self, mock_scraping_class, tmp_path, capsys):
        from src.pipeline_runner import PipelineRunner
        from utils.scraping_handler import ScrapingError

        mock_scraper = Mock()
        mock_scraper.scrape_data.side_effect = ScrapingError("No projects")
        mock_scraping_class.return_value = mock_scraper

        runner = PipelineRunner(data_path=str(tmp_path))
        course = {'name': 'dezoomcamp', 'year': 2024, 'url': 'http://example.com'}

        result = runner._process_course(course)

        assert result is False

    @patch('src.pipeline_runner.ScrapingHandler')
    @patch.object(
        __import__('src.pipeline_runner', fromlist=['PipelineRunner']).PipelineRunner,
        '_run_step',
    )
    def test_process_course_step_failure(
        self, mock_run_step, mock_scraping_class, tmp_path
    ):
        from src.pipeline_runner import PipelineRunner

        mock_scraper = Mock()
        mock_scraper.scrape_data.return_value = ['file.csv']
        mock_scraping_class.return_value = mock_scraper

        mock_run_step.side_effect = RuntimeError("Step failed")

        runner = PipelineRunner(data_path=str(tmp_path))
        course = {'name': 'dezoomcamp', 'year': 2024, 'url': 'http://example.com'}

        result = runner._process_course(course)

        assert result is False


class TestRunStep:
    """Tests for _run_step method."""

    @patch('src.pipeline_runner.subprocess.run')
    def test_run_step_success(self, mock_subprocess):
        from src.pipeline_runner import PipelineRunner

        mock_subprocess.return_value = Mock(returncode=0)

        runner = PipelineRunner()
        course = {'name': 'dezoomcamp', 'year': 2024}

        # Should not raise
        runner._run_step('src.combine_csvs', course)

        mock_subprocess.assert_called_once()

    @patch('src.pipeline_runner.subprocess.run')
    def test_run_step_failure_raises(self, mock_subprocess):
        from src.pipeline_runner import PipelineRunner

        mock_subprocess.return_value = Mock(returncode=1)

        runner = PipelineRunner()
        course = {'name': 'dezoomcamp', 'year': 2024}

        with pytest.raises(RuntimeError, match="failed"):
            runner._run_step('src.combine_csvs', course)

    @patch('src.pipeline_runner.subprocess.run')
    def test_run_step_includes_limit(self, mock_subprocess):
        from src.pipeline_runner import PipelineRunner

        mock_subprocess.return_value = Mock(returncode=0)

        runner = PipelineRunner(limit=5)
        course = {'name': 'dezoomcamp', 'year': 2024}

        runner._run_step('src.combine_csvs', course)

        call_args = mock_subprocess.call_args[0][0]
        assert '--limit' in call_args
        assert '5' in call_args


class TestMainFunction:
    """Tests for main function argument parsing."""

    @patch('src.pipeline_runner.PipelineRunner')
    @patch('src.pipeline_runner.os.environ.get')
    def test_main_discover_mode(self, mock_env, mock_runner_class):
        from src.pipeline_runner import main

        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner

        with patch.object(sys, 'argv', ['pipeline_runner', '--discover']):
            main()

        mock_runner.discover.assert_called_once()

    @patch('src.pipeline_runner.PipelineRunner')
    @patch('src.pipeline_runner.os.environ.get')
    def test_main_checks_env_vars(self, mock_env, mock_runner_class, capsys):
        mock_env.return_value = None  # Missing env vars

        with patch.object(sys, 'argv', ['pipeline_runner']):
            with pytest.raises(SystemExit) as exc_info:
                from src.pipeline_runner import main

                main()

            # Should exit with error
            assert exc_info.value.code == 1
