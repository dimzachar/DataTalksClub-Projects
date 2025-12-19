"""Unit tests for ScrapingHandler utility."""

import os
import tempfile
from unittest.mock import Mock, MagicMock, patch

import pytest

from utils.scraping_handler import ScrapingError, ScrapingHandler


class TestScrapingHandlerInit:
    """Tests for ScrapingHandler initialization."""

    def test_creates_subdirectory(self, tmp_path):
        handler = ScrapingHandler(
            url="https://example.com",
            folder_path=str(tmp_path),
            course="dezoomcamp",
            year=2025,
        )

        expected_dir = tmp_path / "dezoomcamp" / "2025"
        assert expected_dir.exists()

    def test_sets_attributes_correctly(self, tmp_path):
        handler = ScrapingHandler(
            url="https://courses.datatalks.club/de-zoomcamp-2025/projects",
            folder_path=str(tmp_path),
            course="dezoomcamp",
            year=2025,
        )

        assert handler.url == "https://courses.datatalks.club/de-zoomcamp-2025/projects"
        assert handler.course == "dezoomcamp"
        assert handler.year == 2025


class TestScrapeListFormat:
    """Tests for _scrape_list_format method."""

    def test_extracts_github_links_from_list_group(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <div class="list-group-item">
            <a href="https://github.com/user/repo1">Project 1</a>
        </div>
        <div class="list-group-item">
            <a href="https://github.com/user/repo2">Project 2</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)
        projects = handler._scrape_list_format(soup)

        assert len(projects) == 2
        assert "https://github.com/user/repo1" in projects
        assert "https://github.com/user/repo2" in projects

    def test_ignores_non_github_links(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <div class="list-group-item">
            <a href="https://github.com/user/repo">GitHub Project</a>
        </div>
        <div class="list-group-item">
            <a href="https://example.com/other">Other Link</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)
        projects = handler._scrape_list_format(soup)

        assert len(projects) == 1
        assert "github.com" in projects[0]


class TestScrapeTableFormat:
    """Tests for _scrape_table_format method."""

    def test_extracts_github_links_from_table(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr>
                <td><a href="https://github.com/user/repo1">Project 1</a></td>
            </tr>
            <tr>
                <td><a href="https://github.com/user/repo2">Project 2</a></td>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)
        projects = handler._scrape_table_format(soup)

        assert len(projects) == 2

    def test_handles_th_cells(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <table>
            <tr>
                <th><a href="https://github.com/user/repo">Header Link</a></th>
            </tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)
        projects = handler._scrape_table_format(soup)

        assert len(projects) == 1


class TestScrapeData:
    """Tests for scrape_data method."""

    @patch('utils.scraping_handler.requests.get')
    def test_successful_scrape_list_format(self, mock_get, tmp_path):
        html = """
        <html>
        <div class="list-group-item">
            <a href="https://github.com/user/repo1">Project 1</a>
        </div>
        <div class="list-group-item">
            <a href="https://github.com/user/repo2">Project 2</a>
        </div>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        handler = ScrapingHandler(
            url="https://courses.datatalks.club/test/projects",
            folder_path=str(tmp_path),
            course="testcourse",
            year=2025,
        )

        filenames = handler.scrape_data()

        assert len(filenames) == 1
        assert "scraped_data_testcourse_2025.csv" in filenames[0]

        # Verify CSV was created
        csv_path = tmp_path / "testcourse" / "2025" / filenames[0]
        assert csv_path.exists()

    @patch('utils.scraping_handler.requests.get')
    def test_raises_on_request_failure(self, mock_get, tmp_path):
        from requests.exceptions import RequestException

        mock_get.side_effect = RequestException("Network error")

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        with pytest.raises(ScrapingError, match="Failed to fetch"):
            handler.scrape_data()

    @patch('utils.scraping_handler.requests.get')
    def test_raises_when_no_projects_found(self, mock_get, tmp_path):
        html = "<html><body>No projects here</body></html>"
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        with pytest.raises(ScrapingError, match="No projects found"):
            handler.scrape_data()

    @patch('utils.scraping_handler.requests.get')
    def test_falls_back_to_table_format(self, mock_get, tmp_path):
        # HTML with table format only (no list-group)
        html = """
        <html>
        <table>
            <tr><td><a href="https://github.com/user/repo">Project</a></td></tr>
        </table>
        </html>
        """
        mock_response = Mock()
        mock_response.content = html.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)
        filenames = handler.scrape_data()

        assert len(filenames) == 1


class TestScrapingError:
    """Tests for ScrapingError exception."""

    def test_is_exception(self):
        assert issubclass(ScrapingError, Exception)

    def test_can_be_raised_with_message(self):
        with pytest.raises(ScrapingError, match="Custom error"):
            raise ScrapingError("Custom error message")


class TestURLValidation:
    """Tests for _is_valid_github_url method (SSRF prevention)."""

    def test_valid_github_url(self, tmp_path):
        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        assert handler._is_valid_github_url("https://github.com/user/repo") is True
        assert (
            handler._is_valid_github_url("https://github.com/user/repo/tree/main")
            is True
        )
        assert (
            handler._is_valid_github_url(
                "https://github.com/org/project/blob/main/file.py"
            )
            is True
        )

    def test_rejects_non_https(self, tmp_path):
        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        assert handler._is_valid_github_url("http://github.com/user/repo") is False
        assert handler._is_valid_github_url("ftp://github.com/user/repo") is False

    def test_rejects_non_github_domains(self, tmp_path):
        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        assert handler._is_valid_github_url("https://gitlab.com/user/repo") is False
        assert (
            handler._is_valid_github_url("https://evil.com/github.com/user/repo")
            is False
        )
        assert (
            handler._is_valid_github_url("https://github.com.evil.com/user/repo")
            is False
        )

    def test_rejects_localhost_ssrf(self, tmp_path):
        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        assert handler._is_valid_github_url("https://localhost/user/repo") is False
        assert handler._is_valid_github_url("https://127.0.0.1/user/repo") is False
        assert handler._is_valid_github_url("https://192.168.1.1/user/repo") is False

    def test_rejects_empty_path(self, tmp_path):
        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        assert handler._is_valid_github_url("https://github.com/") is False
        assert handler._is_valid_github_url("https://github.com") is False

    def test_handles_malformed_urls(self, tmp_path):
        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)

        assert handler._is_valid_github_url("not-a-url") is False
        assert handler._is_valid_github_url("") is False
        assert handler._is_valid_github_url(None) is False

    def test_scrape_filters_invalid_urls(self, tmp_path):
        """Test that scraping filters out invalid URLs."""
        from bs4 import BeautifulSoup

        html = """
        <div class="list-group-item">
            <a href="https://github.com/user/valid-repo">Valid</a>
        </div>
        <div class="list-group-item">
            <a href="http://github.com/user/insecure">Insecure HTTP</a>
        </div>
        <div class="list-group-item">
            <a href="https://evil.com/github.com/fake">SSRF attempt</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2025)
        projects = handler._scrape_list_format(soup)

        # Only the valid GitHub URL should be included
        assert len(projects) == 1
        assert projects[0] == "https://github.com/user/valid-repo"
