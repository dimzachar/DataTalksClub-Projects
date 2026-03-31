"""
One-click pipeline execution - automatically discovers and processes only NEW courses.

Usage:
    python -m src.pipeline_runner              # Process only missing data
    python -m src.pipeline_runner --all        # Reprocess everything
    python -m src.pipeline_runner --discover   # Just show what's available
    python -m src.pipeline_runner --course dezoomcamp --year 2025  # Single course
    python -m src.pipeline_runner --course dezoomcamp --year 2025 --project-url https://github.com/user/repo  # Single project
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

from utils.course_discovery import CourseDiscovery
from utils.scraping_handler import ScrapingError, ScrapingHandler


class PipelineRunner:
    def __init__(self, data_path="Data", limit=0, project_url=None):
        self.data_path = Path(data_path)
        self.discovery = CourseDiscovery(data_path)
        self.limit = limit  # Limit projects for testing
        self.project_url = project_url

    def discover(self):
        """Show all available courses and their status."""
        print("\n📋 Available courses on DataTalksClub:\n")
        status = self.discovery.get_status()

        if not status:
            print("  No courses found. Check your internet connection.")
            return

        for course in status:
            icon = "✓" if course["has_data"] else "○"
            print(f"  {icon} {course['name']}/{course['year']}")

        have_count = sum(1 for c in status if c["has_data"])
        missing_count = len(status) - have_count
        print(
            f"\n  Total: {len(status)} | Have: {have_count} | Missing: {missing_count}"
        )

    def run(self, force_all=False, course=None, year=None):
        """Run pipeline for missing courses only (or all if force_all=True)."""
        # Single course mode
        if course and year:
            courses = [
                c
                for c in self.discovery.discover_courses()
                if c["name"] == course and c["year"] == year
            ]
            if not courses:
                print(f"❌ Course {course}/{year} not found on DataTalksClub")
                return False
        elif force_all:
            courses = self.discovery.discover_courses()
            print(f"🔄 Force mode: Processing ALL {len(courses)} courses")
        else:
            courses = self.discovery.get_missing_courses()
            if not courses:
                print("\n✅ All courses up to date! Nothing to process.")
                return True
            print(f"\n🚀 Found {len(courses)} new courses to process")

        success_count = 0
        for course_info in courses:
            if self._process_course(course_info):
                success_count += 1

        print(f"\n{'='*50}")
        print(f"✅ Completed: {success_count}/{len(courses)} courses")
        return success_count == len(courses)

    def _process_course(self, course):
        """Run full pipeline for a single course/year."""
        print(f"\n{'='*50}")
        print(f"📦 Processing: {course['name']}/{course['year']}")
        print(f"   Source: {course['url']}")
        print(f"{'='*50}")

        try:
            # Step 1: Scrape from web
            print("\n[1/3] Scraping project URLs...")
            handler = ScrapingHandler(
                url=course["url"],
                folder_path=str(self.data_path),
                course=course["name"],
                year=course["year"],
            )
            try:
                filenames = handler.scrape_data()
                print(f"   ✓ Scraped {len(filenames)} tables")
            except ScrapingError as e:
                print(f"   ⚠️  {e}")
                print(f"   Skipping {course['name']}/{course['year']}")
                return False

            # Step 2: Combine CSVs
            print("\n[2/3] Combining and cleaning CSVs...")
            self._run_step("src.combine_csvs", course)

            # Step 3: Generate titles AND classify deployment/cloud (unified)
            print("\n[3/3] Generating titles & classifying (multi-file context)...")
            self._run_step("src.generate_titles_and_classify", course)

            print(f"\n✅ Completed {course['name']}/{course['year']}")
            return True

        except Exception as e:
            print(f"\n❌ Failed {course['name']}/{course['year']}: {e}")
            return False

    def _run_step(self, module, course):
        """Run a pipeline step as subprocess with live output."""
        cmd = [
            sys.executable,
            "-m",
            module,
            "--course",
            course["name"],
            "--year",
            str(course["year"]),
            "--base_path",
            str(self.data_path),
        ]
        # Add limit if specified
        if self.limit > 0:
            cmd.extend(["--limit", str(self.limit)])
        # Optionally process just one project URL
        if self.project_url and module == "src.generate_titles_and_classify":
            cmd.extend(["--project-url", self.project_url])

        # Stream output in real-time (no capture)
        result = subprocess.run(cmd)

        if result.returncode != 0:
            raise RuntimeError(f"Step {module} failed")


def main():
    parser = argparse.ArgumentParser(
        description="Run data pipeline for DataTalksClub courses"
    )
    parser.add_argument(
        "--all", action="store_true", help="Reprocess all courses (not just missing)"
    )
    parser.add_argument(
        "--discover", action="store_true", help="Just show available courses"
    )
    parser.add_argument(
        "--course", type=str, help="Process specific course (e.g., dezoomcamp)"
    )
    parser.add_argument("--year", type=int, help="Process specific year (e.g., 2025)")
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit projects to process (for testing)"
    )
    parser.add_argument(
        "--project-url",
        "--project_url",
        dest="project_url",
        type=str,
        help="Process only this project URL within the selected course/year",
    )
    args = parser.parse_args()
    if args.project_url and not (args.course and args.year):
        parser.error("--project-url requires --course and --year")

    # Check for required environment variables
    if not args.discover:
        missing_vars = []
        if not os.environ.get("MY_GITHUB_TOKEN"):
            missing_vars.append("MY_GITHUB_TOKEN")
        if not os.environ.get("OPENROUTER_API_KEY"):
            missing_vars.append("OPENROUTER_API_KEY")

        if missing_vars:
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            print("   Set them before running the pipeline:")
            print("   export MY_GITHUB_TOKEN='your_token'")
            print("   export OPENROUTER_API_KEY='your_key'")
            sys.exit(1)

    runner = PipelineRunner(limit=args.limit, project_url=args.project_url)

    if args.discover:
        runner.discover()
    elif args.course and args.year:
        success = runner.run(course=args.course, year=args.year)
        sys.exit(0 if success else 1)
    else:
        success = runner.run(force_all=args.all)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
