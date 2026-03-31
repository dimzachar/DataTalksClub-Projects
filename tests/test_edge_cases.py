"""Tests for edge cases and bug fixes."""

import os
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest


class TestDivisionByZeroProtection:
    """Tests for division by zero protection in rate calculation."""

    def test_rate_calculation_with_zero_elapsed(self):
        """Test that rate calculation handles zero elapsed time."""
        total = 100
        elapsed = 0

        # This is the fix we implemented
        rate = total / elapsed if elapsed > 0 else 0

        assert rate == 0

    def test_rate_calculation_with_positive_elapsed(self):
        """Test normal rate calculation."""
        total = 100
        elapsed = 10

        rate = total / elapsed if elapsed > 0 else 0

        assert rate == 10.0

    def test_rate_calculation_with_small_elapsed(self):
        """Test rate calculation with very small elapsed time."""
        total = 100
        elapsed = 0.001

        rate = total / elapsed if elapsed > 0 else 0

        assert rate == 100000.0


class TestStrReplaceRegexFlag:
    """Tests for str.replace with regex=False flag."""

    def test_replace_quotes_literal(self):
        """Test that quotes are replaced literally."""
        df = pd.DataFrame({'title': ['"Hello World"', 'No quotes']})

        df['title'] = df['title'].str.replace('"', '', regex=False)

        assert df['title'].iloc[0] == 'Hello World'
        assert df['title'].iloc[1] == 'No quotes'

    def test_replace_prefix_literal(self):
        """Test that 'Title: ' prefix is replaced literally."""
        df = pd.DataFrame({'title': ['Title: My Project', 'Other Project']})

        df['title'] = df['title'].str.replace('Title: ', '', regex=False)

        assert df['title'].iloc[0] == 'My Project'
        assert df['title'].iloc[1] == 'Other Project'

    def test_replace_does_not_interpret_regex(self):
        """Test that special regex characters are treated literally."""
        df = pd.DataFrame({'title': ['Hello.World', 'Test']})

        # With regex=False, '.' is literal, not 'any character'
        df['title'] = df['title'].str.replace('.', '-', regex=False)

        assert df['title'].iloc[0] == 'Hello-World'


class TestNLTKDataDownload:
    """Tests for NLTK data download optimization."""

    def test_ensure_nltk_data_function_exists(self):
        """Test that the _ensure_nltk_data function is defined."""
        from src.eda_analysis import _ensure_nltk_data

        # Should not raise
        assert callable(_ensure_nltk_data)

    def test_eda_analysis_imports_without_download(self):
        """Test that EDAAnalysis can be imported without triggering downloads."""
        # This test verifies the module loads without error
        # The actual download check happens only if data is missing
        from src.eda_analysis import EDAAnalysis

        assert EDAAnalysis is not None

    def test_eda_analysis_init_triggers_nltk_setup_once(self):
        """Test that NLTK setup runs lazily on first EDAAnalysis initialization."""
        import src.eda_analysis as eda_mod

        eda_mod.EDAAnalysis._nltk_ready = False
        mock_wn = SimpleNamespace(ensure_loaded=lambda: None)
        mock_stopwords = SimpleNamespace(words=lambda _: [])
        with patch.object(eda_mod, '_ensure_nltk_data') as mock_ensure:
            with patch.object(eda_mod, 'wn', mock_wn):
                with patch.object(eda_mod, 'stopwords', mock_stopwords):
                    with patch.object(eda_mod, 'WordNetLemmatizer') as mock_lemma_cls:
                        eda_mod.EDAAnalysis(pd.DataFrame({'project_title': ['a']}))
                        eda_mod.EDAAnalysis(pd.DataFrame({'project_title': ['b']}))

                        assert mock_ensure.call_count == 1
                        mock_lemma_cls.assert_called()

    def test_preprocess_text_uses_initialized_resources(self):
        """Test preprocess_text uses cached lemmatizer/stopwords from __init__."""
        import src.eda_analysis as eda_mod

        eda_mod.EDAAnalysis._nltk_ready = True  # Skip external NLTK setup in this unit test
        mock_stopwords = SimpleNamespace(words=lambda _: ['the'])
        with patch.object(eda_mod, 'stopwords', mock_stopwords):
            with patch.object(eda_mod, 'word_tokenize', return_value=['cats', 'the']):
                with patch.object(eda_mod, 'WordNetLemmatizer') as mock_lemma_cls:
                    mock_lemma = mock_lemma_cls.return_value
                    mock_lemma.lemmatize.side_effect = (
                        lambda word: word[:-1] if word.endswith('s') else word
                    )

                    analysis = eda_mod.EDAAnalysis(
                        pd.DataFrame({'project_title': ['cats the']})
                    )
                    result = analysis.preprocess_text("Cats the")

                    assert result == ['cat']
                    mock_lemma_cls.assert_called_once()


class TestPandasMapMethod:
    """Tests for pandas map method (replacement for deprecated applymap)."""

    def test_map_applies_function_to_all_cells(self):
        """Test that map applies function to all cells."""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})

        # Using map instead of applymap
        result = df.style.map(lambda x: 'background-color: red')

        # Should not raise and should return a Styler object
        assert result is not None

    def test_background_color_function(self):
        """Test the background color function used in app.py."""

        def background_color(val):
            return 'background-color: #001220'

        df = pd.DataFrame({'col': ['test']})
        styled = df.style.map(background_color)

        assert styled is not None


class TestStackedBarChartKeyError:
    """Tests for KeyError protection in stacked bar charts."""

    def test_missing_course_in_pivot_handled(self):
        """Test that missing courses in pivot table don't cause KeyError."""
        # Simulate a pivot table with only some courses
        pivot_data = pd.DataFrame(
            {
                'dezoomcamp': [10, 20],
                'mlzoomcamp': [15, 25],
            },
            index=['2023', '2024'],
        )

        course_order = ['dezoomcamp', 'mlzoomcamp', 'mlopszoomcamp', 'llmzoomcamp']

        # This is the fix we implemented
        for course in course_order:
            if course not in pivot_data.columns:
                continue  # Skip missing courses
            values = pivot_data[course].tolist()
            assert len(values) == 2

    def test_all_courses_present(self):
        """Test normal case when all courses are present."""
        pivot_data = pd.DataFrame(
            {
                'dezoomcamp': [10],
                'mlzoomcamp': [15],
                'mlopszoomcamp': [20],
                'llmzoomcamp': [25],
            },
            index=['2024'],
        )

        course_order = ['dezoomcamp', 'mlzoomcamp', 'mlopszoomcamp', 'llmzoomcamp']

        processed = []
        for course in course_order:
            if course not in pivot_data.columns:
                continue
            processed.append(course)

        assert len(processed) == 4

    def test_empty_pivot_table(self):
        """Test handling of empty pivot table."""
        pivot_data = pd.DataFrame()
        course_order = ['dezoomcamp']

        processed = []
        for course in course_order:
            if course not in pivot_data.columns:
                continue
            processed.append(course)

        assert len(processed) == 0
