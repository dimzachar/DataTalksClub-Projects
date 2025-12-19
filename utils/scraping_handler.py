import os
import csv
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


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
        Supports both old table format and new list-group format.

        Returns:
            list: List of created CSV filenames

        Raises:
            ScrapingError: If page cannot be fetched or no projects found
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ScrapingError(f"Failed to fetch {self.url}: {e}")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try new format first (list-group with GitHub links)
        projects = self._scrape_list_format(soup)

        # Fall back to old table format
        if not projects:
            projects = self._scrape_table_format(soup)

        if not projects:
            raise ScrapingError(
                f"No projects found at {self.url}. "
                f"The course {self.course}/{self.year} may not have projects yet."
            )

        # Save to CSV
        file_name = f"scraped_data_{self.course}_{self.year}.csv"
        file_path = f"{self.subdirectory}/{file_name}"

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['project_url'])  # Header
            for url in projects:
                csvwriter.writerow([url])

        print(f"   Saved {len(projects)} projects to {file_path}")
        return [file_name]

    def _is_valid_github_url(self, url):
        """Validate that URL is a legitimate GitHub URL to prevent SSRF."""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme == 'https'
                and parsed.netloc == 'github.com'
                and len(parsed.path) > 1  # Must have a path beyond /
            )
        except Exception:
            return False

    def _scrape_list_format(self, soup):
        """Scrape from new list-group format (2025+ courses)."""
        projects = []

        # Find all links in list-group-item divs that point to GitHub
        for item in soup.find_all('div', class_='list-group-item'):
            link = item.find('a', href=True)
            if link and 'github.com' in link['href']:
                url = link['href']
                if self._is_valid_github_url(url):
                    projects.append(url)

        return projects

    def _scrape_table_format(self, soup):
        """Scrape from old table format (legacy courses)."""
        projects = []

        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                for cell in row.find_all(['td', 'th']):
                    link = cell.find('a', href=True)
                    if link and 'github.com' in link['href']:
                        url = link['href']
                        if self._is_valid_github_url(url):
                            projects.append(url)

        return projects
