"""
Discover available courses by scraping the DataTalksClub homepage.
Only processes FINISHED courses we care about, skips data we already have.
"""

import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Courses we want to track (map URL slug prefix → folder name)
TRACKED_COURSES = {
    "de-zoomcamp": "dezoomcamp",
    "ml-zoomcamp": "mlzoomcamp",
    "mlops-zoomcamp": "mlopszoomcamp",
    "llm-zoomcamp": "llmzoomcamp",
}


class CourseDiscovery:
    BASE_URL = "https://courses.datatalks.club"

    def __init__(self, data_path="Data"):
        self.data_path = Path(data_path)

    def discover_courses(self):
        """Scrape homepage to find only FINISHED courses (skip active ones)."""
        try:
            response = requests.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching homepage: {e}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")

        courses = []
        seen = set()

        # Find the "Finished courses" section
        in_finished_section = False

        for element in soup.find_all(["h3", "li"]):
            # Check if we're entering the finished courses section
            if element.name == "h3":
                text = element.get_text(strip=True).lower()
                in_finished_section = "finished" in text
                continue

            # Only process links in the finished section
            if not in_finished_section:
                continue

            link = element.find("a", href=True)
            if not link:
                continue

            href = link["href"]

            # Match pattern like "/de-zoomcamp-2024" or "/ml-zoomcamp-2023"
            match = re.search(r"/([a-z]+-zoomcamp-(\d{4}))", href)
            if not match:
                continue

            course_slug = match.group(1)  # e.g., "de-zoomcamp-2024"
            year = int(match.group(2))

            # Avoid duplicates
            if course_slug in seen:
                continue
            seen.add(course_slug)

            # Map to our folder naming convention
            for slug_prefix, folder_name in TRACKED_COURSES.items():
                if course_slug.startswith(slug_prefix):
                    courses.append(
                        {
                            "name": folder_name,
                            "year": year,
                            "slug": course_slug,
                            "url": f"{self.BASE_URL}/{course_slug}/projects",
                        }
                    )
                    break

        # Sort by year descending (newest first)
        courses.sort(key=lambda x: (x["name"], -x["year"]))
        return courses

    def get_missing_courses(self):
        """Return only courses we don't have data for yet."""
        all_courses = self.discover_courses()
        missing = []

        for course in all_courses:
            data_file = (
                self.data_path / course["name"] / str(course["year"]) / "data.csv"
            )
            if not data_file.exists():
                missing.append(course)
            else:
                print(f"✓ Already have: {course['name']}/{course['year']}")

        return missing

    def get_status(self):
        """Return all courses with their status (have data or not)."""
        all_courses = self.discover_courses()
        status = []

        for course in all_courses:
            data_file = (
                self.data_path / course["name"] / str(course["year"]) / "data.csv"
            )
            status.append(
                {
                    **course,
                    "has_data": data_file.exists(),
                }
            )

        return status
