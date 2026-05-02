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


class TestScrapeArticleFormat:
    """Tests for _scrape_article_format method (current site design)."""

    def test_extracts_github_links_from_articles(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <article>
            <a href="https://github.com/user/repo1">Happy Boyd</a>
            <span>32</span>
        </article>
        <article>
            <a href="https://github.com/user/repo2">Ogabby</a>
            <span>30</span>
        </article>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        projects = handler._scrape_article_format(soup)

        assert len(projects) == 2
        assert ("https://github.com/user/repo1", "32") in projects
        assert ("https://github.com/user/repo2", "30") in projects

    def test_captures_score(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <article>
            <a href="https://github.com/user/repo">Project</a>
            <span>28</span>
        </article>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        projects = handler._scrape_article_format(soup)

        assert projects[0][1] == "28"

    def test_score_empty_when_no_span(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <article>
            <a href="https://github.com/user/repo">Project</a>
        </article>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        projects = handler._scrape_article_format(soup)

        assert projects[0][1] == ''

    def test_ignores_non_github_links(self, tmp_path):
        from bs4 import BeautifulSoup

        html = """
        <article>
            <a href="https://github.com/user/repo">GitHub Project</a>
        </article>
        <article>
            <a href="https://example.com/other">Other Link</a>
        </article>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        projects = handler._scrape_article_format(soup)

        assert len(projects) == 1
        assert projects[0][0] == "https://github.com/user/repo"

    def test_returns_empty_when_no_articles(self, tmp_path):
        from bs4 import BeautifulSoup

        html = "<html><body><p>No articles here</p></body></html>"
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        projects = handler._scrape_article_format(soup)

        assert projects == []


class TestScrapeTableFormat:
    """Tests for _scrape_table_format method (legacy fallback)."""

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
        assert all(score == '' for _, score in projects)

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
    def test_successful_scrape_article_format(self, mock_get, tmp_path):
        html = """
        <html>
        <article><a href="https://github.com/user/repo1">Project 1</a><span>30</span></article>
        <article><a href="https://github.com/user/repo2">Project 2</a><span>28</span></article>
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
            year=2026,
        )
        filenames = handler.scrape_data()

        assert len(filenames) == 1
        assert "scraped_data_testcourse_2026.csv" in filenames[0]

        csv_path = tmp_path / "testcourse" / "2026" / filenames[0]
        assert csv_path.exists()

        import csv as csv_mod
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv_mod.reader(f))
        assert rows[0] == ['project_url', 'score']
        assert rows[1] == ['https://github.com/user/repo1', '30']

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

    @patch('utils.scraping_handler.requests.get')
    def test_pagination_fetches_all_pages(self, mock_get, tmp_path):
        """Scraper should follow ?page=N links until no next page."""
        page1_html = """
        <html>
        <article><a href="https://github.com/user/repo1">P1</a><span>32</span></article>
        <nav><a aria-label="Next page" href="?page=2">→</a></nav>
        </html>
        """
        page2_html = """
        <html>
        <article><a href="https://github.com/user/repo2">P2</a><span>30</span></article>
        </html>
        """

        mock_resp1 = Mock()
        mock_resp1.content = page1_html.encode()
        mock_resp1.raise_for_status = Mock()

        mock_resp2 = Mock()
        mock_resp2.content = page2_html.encode()
        mock_resp2.raise_for_status = Mock()

        mock_get.side_effect = [mock_resp1, mock_resp2]

        handler = ScrapingHandler(
            url="https://courses.datatalks.club/test/projects",
            folder_path=str(tmp_path),
            course="testcourse",
            year=2026,
        )
        filenames = handler.scrape_data()

        assert mock_get.call_count == 2
        assert mock_get.call_args_list[1][0][0].endswith("?page=2")

        import csv as csv_mod
        csv_path = tmp_path / "testcourse" / "2026" / filenames[0]
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv_mod.reader(f))
        assert len(rows) == 3  # header + 2 projects

    @patch('utils.scraping_handler.requests.get')
    def test_deduplicates_across_pages(self, mock_get, tmp_path):
        """Duplicate URLs across pages should only appear once."""
        dupe_html = """
        <html>
        <article><a href="https://github.com/user/repo1">P1</a><span>32</span></article>
        <nav><a aria-label="Next page" href="?page=2">→</a></nav>
        </html>
        """
        dupe_html2 = """
        <html>
        <article><a href="https://github.com/user/repo1">P1 again</a><span>32</span></article>
        </html>
        """
        mock_resp1 = Mock()
        mock_resp1.content = dupe_html.encode()
        mock_resp1.raise_for_status = Mock()
        mock_resp2 = Mock()
        mock_resp2.content = dupe_html2.encode()
        mock_resp2.raise_for_status = Mock()
        mock_get.side_effect = [mock_resp1, mock_resp2]

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        filenames = handler.scrape_data()

        import csv as csv_mod
        csv_path = tmp_path / "test" / "2026" / filenames[0]
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv_mod.reader(f))
        assert len(rows) == 2  # header + 1 unique project


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
        <article>
            <a href="https://github.com/user/valid-repo">Valid</a>
        </article>
        <article>
            <a href="http://github.com/user/insecure">Insecure HTTP</a>
        </article>
        <article>
            <a href="https://evil.com/github.com/fake">SSRF attempt</a>
        </article>
        """
        soup = BeautifulSoup(html, 'html.parser')

        handler = ScrapingHandler("url", str(tmp_path), "test", 2026)
        projects = handler._scrape_article_format(soup)

        assert len(projects) == 1
        assert projects[0][0] == "https://github.com/user/valid-repo"
