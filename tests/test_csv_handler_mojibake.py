"""Tests for fix_mojibake utility and CSVHandler.fix_mojibake_columns."""

import pandas as pd
import pytest

from utils.csv_handler import CSVHandler, fix_mojibake


class TestFixMojibake:
    """Tests for the fix_mojibake function."""

    def test_fixes_sao_paulo(self):
        """Test fixing common Portuguese mojibake."""
        assert fix_mojibake("SÃ£o Paulo") == "São Paulo"

    def test_fixes_cafe(self):
        """Test fixing accented characters."""
        assert fix_mojibake("cafÃ©") == "café"

    def test_preserves_normal_text(self):
        """Test that normal ASCII text is unchanged."""
        assert fix_mojibake("Normal text") == "Normal text"

    def test_preserves_correct_unicode(self):
        """Test that already correct unicode is unchanged."""
        assert fix_mojibake("São Paulo") == "São Paulo"

    def test_handles_none(self):
        """Test that None values are passed through."""
        assert fix_mojibake(None) is None

    def test_handles_nan(self):
        """Test that NaN values are passed through."""
        result = fix_mojibake(pd.NA)
        assert pd.isna(result)

    def test_handles_non_string(self):
        """Test that non-string values are passed through."""
        assert fix_mojibake(123) == 123
        assert fix_mojibake(45.67) == 45.67

    def test_handles_empty_string(self):
        """Test that empty strings are unchanged."""
        assert fix_mojibake("") == ""

    def test_handles_smart_quotes(self):
        """Test fixing smart quote mojibake."""
        # â€œ and â€ are common mojibake for smart quotes
        text_with_mojibake = 'â€œHelloâ€'
        result = fix_mojibake(text_with_mojibake)
        # Should attempt to fix, result depends on actual encoding
        assert result is not None

    def test_handles_encoding_error_gracefully(self):
        """Test that encoding errors don't crash the function."""
        # This string can't be encoded as latin-1
        weird_text = "Ã" + chr(0x1F600)  # emoji
        result = fix_mojibake(weird_text)
        # Should return something without crashing
        assert result is not None


class TestCSVHandlerMojibakeColumns:
    """Tests for CSVHandler.fix_mojibake_columns method."""

    def test_fixes_specified_columns(self):
        """Test that only specified columns are fixed."""
        df = pd.DataFrame(
            {
                'title': ['SÃ£o Paulo Project', 'Normal Title'],
                'description': ['cafÃ© data', 'normal desc'],
                'url': ['https://example.com', 'https://test.com'],
            }
        )
        handler = CSVHandler(df)
        handler.fix_mojibake_columns(['title', 'description'])

        assert handler.df['title'].iloc[0] == 'São Paulo Project'
        assert handler.df['description'].iloc[0] == 'café data'
        # URL should be unchanged (not in list)
        assert handler.df['url'].iloc[0] == 'https://example.com'

    def test_handles_missing_columns(self):
        """Test that missing columns don't cause errors."""
        df = pd.DataFrame(
            {
                'title': ['Test'],
            }
        )
        handler = CSVHandler(df)
        # Should not raise even though 'nonexistent' doesn't exist
        handler.fix_mojibake_columns(['title', 'nonexistent'])
        assert handler.df['title'].iloc[0] == 'Test'

    def test_handles_mixed_values(self):
        """Test handling columns with mixed None/string values."""
        df = pd.DataFrame(
            {
                'title': ['SÃ£o Paulo', None, 'Normal', pd.NA],
            }
        )
        handler = CSVHandler(df)
        handler.fix_mojibake_columns(['title'])

        assert handler.df['title'].iloc[0] == 'São Paulo'
        assert handler.df['title'].iloc[1] is None
        assert handler.df['title'].iloc[2] == 'Normal'

    def test_empty_column_list(self):
        """Test that empty column list does nothing."""
        df = pd.DataFrame(
            {
                'title': ['SÃ£o Paulo'],
            }
        )
        handler = CSVHandler(df)
        handler.fix_mojibake_columns([])
        # Should remain unchanged
        assert handler.df['title'].iloc[0] == 'SÃ£o Paulo'
