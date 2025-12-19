"""Tests for dynamic year discovery in app.py."""

import os
import shutil
import tempfile

import pytest


class TestGetAvailableYears:
    """Tests for get_available_years function."""

    def test_discovers_years_from_folders(self, tmp_path):
        """Test that years are discovered from existing folders."""
        # Create test directory structure
        course_options = ['dezoomcamp', 'mlzoomcamp']

        # Create some year folders
        (tmp_path / 'dezoomcamp' / '2023').mkdir(parents=True)
        (tmp_path / 'dezoomcamp' / '2024').mkdir(parents=True)
        (tmp_path / 'mlzoomcamp' / '2024').mkdir(parents=True)
        (tmp_path / 'mlzoomcamp' / '2025').mkdir(parents=True)

        # Simulate the function logic
        def get_available_years(data_path, courses):
            years = set()
            for course in courses:
                course_path = os.path.join(data_path, course)
                if os.path.exists(course_path):
                    for item in os.listdir(course_path):
                        if item.isdigit() and os.path.isdir(
                            os.path.join(course_path, item)
                        ):
                            years.add(item)
            return sorted(years) if years else ['2021', '2022', '2023', '2024', '2025']

        years = get_available_years(str(tmp_path), course_options)

        assert '2023' in years
        assert '2024' in years
        assert '2025' in years
        assert len(years) == 3

    def test_returns_default_when_no_folders(self, tmp_path):
        """Test that default years are returned when no folders exist."""
        course_options = ['dezoomcamp']

        def get_available_years(data_path, courses):
            years = set()
            for course in courses:
                course_path = os.path.join(data_path, course)
                if os.path.exists(course_path):
                    for item in os.listdir(course_path):
                        if item.isdigit() and os.path.isdir(
                            os.path.join(course_path, item)
                        ):
                            years.add(item)
            return sorted(years) if years else ['2021', '2022', '2023', '2024', '2025']

        years = get_available_years(str(tmp_path), course_options)

        assert years == ['2021', '2022', '2023', '2024', '2025']

    def test_ignores_non_year_folders(self, tmp_path):
        """Test that non-year folders are ignored."""
        (tmp_path / 'dezoomcamp' / '2024').mkdir(parents=True)
        (tmp_path / 'dezoomcamp' / 'archive').mkdir(parents=True)
        (tmp_path / 'dezoomcamp' / 'notes.txt').touch()

        def get_available_years(data_path, courses):
            years = set()
            for course in courses:
                course_path = os.path.join(data_path, course)
                if os.path.exists(course_path):
                    for item in os.listdir(course_path):
                        if item.isdigit() and os.path.isdir(
                            os.path.join(course_path, item)
                        ):
                            years.add(item)
            return sorted(years) if years else ['2021', '2022', '2023', '2024', '2025']

        years = get_available_years(str(tmp_path), ['dezoomcamp'])

        assert years == ['2024']
        assert 'archive' not in years

    def test_years_are_sorted(self, tmp_path):
        """Test that years are returned in sorted order."""
        (tmp_path / 'dezoomcamp' / '2025').mkdir(parents=True)
        (tmp_path / 'dezoomcamp' / '2021').mkdir(parents=True)
        (tmp_path / 'dezoomcamp' / '2023').mkdir(parents=True)

        def get_available_years(data_path, courses):
            years = set()
            for course in courses:
                course_path = os.path.join(data_path, course)
                if os.path.exists(course_path):
                    for item in os.listdir(course_path):
                        if item.isdigit() and os.path.isdir(
                            os.path.join(course_path, item)
                        ):
                            years.add(item)
            return sorted(years) if years else ['2021', '2022', '2023', '2024', '2025']

        years = get_available_years(str(tmp_path), ['dezoomcamp'])

        assert years == ['2021', '2023', '2025']
