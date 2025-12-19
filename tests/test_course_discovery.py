"""Unit tests for CourseDiscovery utility."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from utils.course_discovery import TRACKED_COURSES, CourseDiscovery


class TestTrackedCourses:
    """Tests for TRACKED_COURSES configuration."""

    def test_dezoomcamp_tracked(self):
        assert "de-zoomcamp" in TRACKED_COURSES
        assert TRACKED_COURSES["de-zoomcamp"] == "dezoomcamp"

    def test_mlzoomcamp_tracked(self):
        assert "ml-zoomcamp" in TRACKED_COURSES
        assert TRACKED_COURSES["ml-zoomcamp"] == "mlzoomcamp"

    def test_mlopszoomcamp_tracked(self):
        assert "mlops-zoomcamp" in TRACKED_COURSES
        assert TRACKED_COURSES["mlops-zoomcamp"] == "mlopszoomcamp"

    def test_llmzoomcamp_tracked(self):
        assert "llm-zoomcamp" in TRACKED_COURSES
        assert TRACKED_COURSES["llm-zoomcamp"] == "llmzoomcamp"


class TestCourseDiscoveryInit:
    """Tests for CourseDiscovery initialization."""

    def test_default_data_path(self):
        discovery = CourseDiscovery()
        assert discovery.data_path == Path("Data")

    def test_custom_data_path(self):
        discovery = CourseDiscovery(data_path="/custom/path")
        assert discovery.data_path == Path("/custom/path")


class TestDiscoverCourses:
    """Tests for discover_courses method."""

    @patch('utils.course_discovery.requests.get')
    def test_parses_finished_courses(self, mock_get):
        html = """
        <html>
        <h3>Finished courses</h3>
        <ul>
            <li><a href="/de-zoomcamp-2024">DE Zoomcamp 2024</a></li>
            <li><a href="/ml-zoomcamp-2023">ML Zoomcamp 2023</a></li>
        </ul>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        assert len(courses) == 2
        course_names = [c['name'] for c in courses]
        assert 'dezoomcamp' in course_names
        assert 'mlzoomcamp' in course_names

    @patch('utils.course_discovery.requests.get')
    def test_ignores_active_courses(self, mock_get):
        html = """
        <html>
        <h3>Active courses</h3>
        <ul>
            <li><a href="/de-zoomcamp-2025">DE Zoomcamp 2025</a></li>
        </ul>
        <h3>Finished courses</h3>
        <ul>
            <li><a href="/de-zoomcamp-2024">DE Zoomcamp 2024</a></li>
        </ul>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        # Should only include finished course
        assert len(courses) == 1
        assert courses[0]['year'] == 2024

    @patch('utils.course_discovery.requests.get')
    def test_extracts_year_correctly(self, mock_get):
        html = """
        <html>
        <h3>Finished courses</h3>
        <li><a href="/de-zoomcamp-2024">Course</a></li>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        assert courses[0]['year'] == 2024

    @patch('utils.course_discovery.requests.get')
    def test_builds_correct_url(self, mock_get):
        html = """
        <html>
        <h3>Finished courses</h3>
        <li><a href="/de-zoomcamp-2024">Course</a></li>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        assert (
            courses[0]['url']
            == "https://courses.datatalks.club/de-zoomcamp-2024/projects"
        )

    @patch('utils.course_discovery.requests.get')
    def test_handles_request_error(self, mock_get):
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Network error")

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        assert courses == []

    @patch('utils.course_discovery.requests.get')
    def test_deduplicates_courses(self, mock_get):
        html = """
        <html>
        <h3>Finished courses</h3>
        <li><a href="/de-zoomcamp-2024">Course 1</a></li>
        <li><a href="/de-zoomcamp-2024">Course 1 Duplicate</a></li>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        discovery = CourseDiscovery()
        courses = discovery.discover_courses()

        assert len(courses) == 1


class TestGetMissingCourses:
    """Tests for get_missing_courses method."""

    @patch.object(CourseDiscovery, 'discover_courses')
    def test_returns_courses_without_data(self, mock_discover, tmp_path):
        mock_discover.return_value = [
            {
                'name': 'dezoomcamp',
                'year': 2024,
                'slug': 'de-zoomcamp-2024',
                'url': 'url1',
            },
            {
                'name': 'dezoomcamp',
                'year': 2023,
                'slug': 'de-zoomcamp-2023',
                'url': 'url2',
            },
        ]

        # Create data for 2023 only
        data_dir = tmp_path / "dezoomcamp" / "2023"
        data_dir.mkdir(parents=True)
        (data_dir / "data.csv").write_text("project_url\nurl")

        discovery = CourseDiscovery(data_path=str(tmp_path))
        missing = discovery.get_missing_courses()

        assert len(missing) == 1
        assert missing[0]['year'] == 2024

    @patch.object(CourseDiscovery, 'discover_courses')
    def test_returns_empty_when_all_present(self, mock_discover, tmp_path):
        mock_discover.return_value = [
            {
                'name': 'dezoomcamp',
                'year': 2024,
                'slug': 'de-zoomcamp-2024',
                'url': 'url',
            },
        ]

        # Create data
        data_dir = tmp_path / "dezoomcamp" / "2024"
        data_dir.mkdir(parents=True)
        (data_dir / "data.csv").write_text("project_url\nurl")

        discovery = CourseDiscovery(data_path=str(tmp_path))
        missing = discovery.get_missing_courses()

        assert len(missing) == 0


class TestGetStatus:
    """Tests for get_status method."""

    @patch.object(CourseDiscovery, 'discover_courses')
    def test_returns_status_for_all_courses(self, mock_discover, tmp_path):
        mock_discover.return_value = [
            {
                'name': 'dezoomcamp',
                'year': 2024,
                'slug': 'de-zoomcamp-2024',
                'url': 'url1',
            },
            {
                'name': 'dezoomcamp',
                'year': 2023,
                'slug': 'de-zoomcamp-2023',
                'url': 'url2',
            },
        ]

        # Create data for 2023 only
        data_dir = tmp_path / "dezoomcamp" / "2023"
        data_dir.mkdir(parents=True)
        (data_dir / "data.csv").write_text("project_url\nurl")

        discovery = CourseDiscovery(data_path=str(tmp_path))
        status = discovery.get_status()

        assert len(status) == 2

        status_2024 = next(s for s in status if s['year'] == 2024)
        status_2023 = next(s for s in status if s['year'] == 2023)

        assert status_2024['has_data'] is False
        assert status_2023['has_data'] is True
