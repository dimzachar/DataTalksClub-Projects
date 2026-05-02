import csv
import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MAX_PAGES = 100  # Safety cap to prevent infinite pagination loops


class ScrapingError(Exception):
    """Custom exception for scraping errors."""

    pass


class ScrapingHandler:
    def __init__(self, url, folder_path, course, year):
        self.url = url
        self.folder_path = folder_path
        self.course = course
        self.year = year
        self.subdirectory = f"{folder_path}/{course}/{year}"
        if not os.path.exists(self.subdirectory):
            os.makedirs(self.subdirectory)

    def scrape_data(self):
        """
        Scrape project URLs from the course page.
        Supports paginated article format (2026+ redesign) and legacy table format.

        Returns:
            list: List of created CSV filenames

        Raises:
            ScrapingError: If page cannot be fetched or no projects found
        """
        projects = []  # list of (url, score) tuples
        seen_urls = set()
        page = 1

        while page <= MAX_PAGES:
            url = f"{self.url}?page={page}" if page > 1 else self.url
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                raise ScrapingError(f"Failed to fetch {url}: {e}")

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try article format first (current site design)
            page_projects = self._scrape_article_format(soup)

            # Fall back to legacy table format
            if not page_projects:
                page_projects = self._scrape_table_format(soup)

            # Deduplicate across pages
            for project_url, score in page_projects:
                if project_url not in seen_urls:
                    seen_urls.add(project_url)
                    projects.append((project_url, score))

            # Stop if no next page link
            next_link = soup.find('a', attrs={'aria-label': 'Next page'})
            if not next_link or not page_projects:
                break

            page += 1
            print(f"   Fetching page {page}...")

        if not projects:
            raise ScrapingError(
                f"No projects found at {self.url}. "
                f"The course {self.course}/{self.year} may not have projects yet."
            )

        # Save to CSV — score column stored but not used by downstream pipeline
        file_name = f"scraped_data_{self.course}_{self.year}.csv"
        file_path = f"{self.subdirectory}/{file_name}"

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['project_url', 'score'])
            for project_url, score in projects:
                csvwriter.writerow([project_url, score])

        print(f"   Saved {len(projects)} projects to {file_path}")
        return [file_name]

    def _is_valid_github_url(self, url):
        """Validate that URL is a legitimate GitHub URL to prevent SSRF."""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme == 'https'
                and parsed.netloc == 'github.com'
                and len(parsed.path) > 1
            )
        except Exception:
            return False

    def _scrape_article_format(self, soup):
        """Scrape from paginated article format (current site design).

        Returns list of (url, score) tuples.
        """
        projects = []

        for article in soup.find_all('article'):
            link = article.find('a', href=True)
            if not link or 'github.com' not in link['href']:
                continue
            url = link['href']
            if not self._is_valid_github_url(url):
                continue
            span = article.find('span')
            score = span.get_text(strip=True) if span else ''
            projects.append((url, score))

        return projects

    def _scrape_table_format(self, soup):
        """Scrape from legacy table format.

        Returns list of (url, score) tuples. Score not available in this format.
        """
        projects = []

        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                for cell in row.find_all(['td', 'th']):
                    link = cell.find('a', href=True)
                    if link and 'github.com' in link['href']:
                        url = link['href']
                        if self._is_valid_github_url(url):
                            projects.append((url, ''))

        return projects
