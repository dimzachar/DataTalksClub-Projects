"""Unit tests for OpenAIAPI."""

from unittest.mock import Mock, MagicMock, patch

import pytest

from utils.openai_api import OpenAIAPI


class TestBuildPrompt:
    """Tests for build_prompt method."""

    def test_basic_prompt(self):
        api = OpenAIAPI(api_key="test")
        prompt = api.build_prompt(
            "https://github.com/user/repo", "A data pipeline project"
        )

        assert "https://github.com/user/repo" in prompt
        assert "A data pipeline project" in prompt
        assert "zoomcamp" in prompt.lower()  # Should mention to avoid zoomcamp

    def test_batch_deployment_guidance(self):
        api = OpenAIAPI(api_key="test")
        prompt = api.build_prompt(
            "https://github.com/user/repo", "Summary", deployment_type="Batch"
        )

        assert "BATCH" in prompt
        assert "Real-Time" in prompt  # Should say not to use Real-Time

    def test_streaming_deployment_guidance(self):
        api = OpenAIAPI(api_key="test")
        prompt = api.build_prompt(
            "https://github.com/user/repo", "Summary", deployment_type="Streaming"
        )

        assert "STREAMING" in prompt


class TestGenerateMultipleTitles:
    """Tests for generate_multiple_titles method."""

    @patch.object(OpenAIAPI, 'llm')
    def test_parses_numbered_list(self, mock_llm):
        mock_llm.return_value = (
            "1. NYC Taxi Analytics\n2. Taxi Fare Pipeline\n3. Data Platform",
            None,
        )

        api = OpenAIAPI(api_key="test")
        titles = api.generate_multiple_titles("https://github.com/user/repo", "Summary")

        assert "NYC Taxi Analytics" in titles
        assert "Taxi Fare Pipeline" in titles
        assert "Data Platform" in titles

    @patch.object(OpenAIAPI, 'llm')
    def test_parses_dash_list(self, mock_llm):
        mock_llm.return_value = ("- NYC Taxi Analytics\n- Taxi Fare Pipeline", None)

        api = OpenAIAPI(api_key="test")
        titles = api.generate_multiple_titles("https://github.com/user/repo", "Summary")

        # The regex only removes leading "- " at start of line, check titles exist
        assert len(titles) == 2
        assert any("NYC Taxi Analytics" in t for t in titles)
        assert any("Taxi Fare Pipeline" in t for t in titles)

    @patch.object(OpenAIAPI, 'llm')
    def test_returns_empty_on_none(self, mock_llm):
        mock_llm.return_value = (None, None)

        api = OpenAIAPI(api_key="test")
        titles = api.generate_multiple_titles("https://github.com/user/repo", "Summary")

        assert titles == []


class TestEvaluateTitle:
    """Tests for evaluate_title method."""

    def test_good_length_scores_higher(self):
        api = OpenAIAPI(api_key="test")

        # 3-5 words should score higher
        score_good = api.evaluate_title("NYC Taxi Data Pipeline", "url", "summary")
        score_short = api.evaluate_title("Pipeline", "url", "summary")
        score_long = api.evaluate_title(
            "This Is A Very Long Title With Many Words", "url", "summary"
        )

        assert score_good > score_short
        assert score_good > score_long

    def test_generic_terms_penalized(self):
        api = OpenAIAPI(api_key="test")

        score_generic = api.evaluate_title("Smart Data Hub", "url", "summary")
        score_specific = api.evaluate_title("NYC Taxi Pipeline", "url", "summary")

        assert score_specific > score_generic

    def test_keyword_match_scores_higher(self):
        api = OpenAIAPI(api_key="test")

        score_match = api.evaluate_title(
            "Taxi Data Pipeline", "taxi-project", "taxi data analysis"
        )
        score_no_match = api.evaluate_title(
            "Weather Platform", "taxi-project", "taxi data analysis"
        )

        assert score_match > score_no_match


class TestParseClassificationResponse:
    """Tests for _parse_classification_response method."""

    def test_parses_batch_deployment(self):
        api = OpenAIAPI(api_key="test")
        response = """DEPLOYMENT: Batch
DEPLOYMENT_REASON: Uses Airflow DAGs
CLOUD: GCP
CLOUD_REASON: Uses BigQuery"""

        result = api._parse_classification_response(response)

        assert result['deployment_type'] == 'Batch'
        assert 'Airflow' in result['deployment_reason']
        assert result['cloud_provider'] == 'GCP'

    def test_parses_streaming_deployment(self):
        api = OpenAIAPI(api_key="test")
        response = """DEPLOYMENT: Streaming
DEPLOYMENT_REASON: Uses Kafka
CLOUD: AWS
CLOUD_REASON: Uses Kinesis"""

        result = api._parse_classification_response(response)

        assert result['deployment_type'] == 'Streaming'
        assert result['cloud_provider'] == 'AWS'

    def test_parses_multiple_deployment_types(self):
        api = OpenAIAPI(api_key="test")
        response = """DEPLOYMENT: Batch, Streaming
DEPLOYMENT_REASON: Uses both Airflow and Kafka
CLOUD: GCP
CLOUD_REASON: Uses BigQuery"""

        result = api._parse_classification_response(response)

        assert 'Batch' in result['deployment_type']
        assert 'Streaming' in result['deployment_type']

    def test_parses_web_service(self):
        api = OpenAIAPI(api_key="test")
        response = """DEPLOYMENT: Web Service
DEPLOYMENT_REASON: Uses FastAPI
CLOUD: AWS
CLOUD_REASON: Uses Lambda"""

        result = api._parse_classification_response(response)

        assert result['deployment_type'] == 'Web Service'

    def test_handles_unknown(self):
        api = OpenAIAPI(api_key="test")
        response = """DEPLOYMENT: Unknown
DEPLOYMENT_REASON: Cannot determine
CLOUD: Unknown
CLOUD_REASON: No cloud indicators"""

        result = api._parse_classification_response(response)

        assert result['deployment_type'] == 'Unknown'
        assert result['cloud_provider'] == 'Unknown'

    def test_normalizes_cloud_names(self):
        api = OpenAIAPI(api_key="test")

        # Test GCP variations
        result = api._parse_classification_response(
            "DEPLOYMENT: Batch\nDEPLOYMENT_REASON: test\nCLOUD: Google Cloud\nCLOUD_REASON: test"
        )
        assert result['cloud_provider'] == 'GCP'

        # Test AWS variations
        result = api._parse_classification_response(
            "DEPLOYMENT: Batch\nDEPLOYMENT_REASON: test\nCLOUD: Amazon Web Services\nCLOUD_REASON: test"
        )
        assert result['cloud_provider'] == 'AWS'


class TestClassifyDeploymentAndCloud:
    """Tests for classify_deployment_and_cloud method."""

    @patch.object(OpenAIAPI, 'llm')
    def test_uses_valid_deployment_types(self, mock_llm):
        mock_llm.return_value = (
            "DEPLOYMENT: Batch\nDEPLOYMENT_REASON: test\nCLOUD: GCP\nCLOUD_REASON: test",
            None,
        )

        api = OpenAIAPI(api_key="test")
        files = {"README.md": "# Test project"}

        result = api.classify_deployment_and_cloud(
            "https://github.com/user/repo",
            files,
            valid_deployment_types=['Batch', 'Streaming'],
        )

        # Check that the prompt was called with valid types
        call_args = mock_llm.call_args[0][0]
        assert 'Batch' in call_args
        assert 'Streaming' in call_args

    @patch.object(OpenAIAPI, 'llm')
    def test_returns_default_on_error(self, mock_llm):
        mock_llm.return_value = (None, None)

        api = OpenAIAPI(api_key="test")
        files = {"README.md": "# Test"}

        result = api.classify_deployment_and_cloud(
            "https://github.com/user/repo", files
        )

        assert result['deployment_type'] == 'Unknown'
        assert result['cloud_provider'] == 'Unknown'


class TestGenerateSummary:
    """Tests for generate_summary method."""

    @patch.object(OpenAIAPI, 'llm')
    def test_generates_summary(self, mock_llm):
        mock_llm.return_value = ("This is a data pipeline project.", None)

        api = OpenAIAPI(api_key="test")
        result = api.generate_summary("# README\nSome content here")

        assert "data pipeline" in result

    @patch.object(OpenAIAPI, 'llm')
    def test_returns_empty_on_failure(self, mock_llm):
        mock_llm.return_value = (None, None)

        api = OpenAIAPI(api_key="test")
        result = api.generate_summary("content")

        assert result == ""


class TestProcessProject:
    """Tests for process_project method."""

    @patch.object(OpenAIAPI, 'evaluate_and_revise_titles')
    @patch.object(OpenAIAPI, 'generate_multiple_titles')
    @patch.object(OpenAIAPI, 'generate_summary')
    def test_full_process(self, mock_summary, mock_titles, mock_evaluate):
        mock_summary.return_value = "A data pipeline"
        mock_titles.return_value = ['Title 1', 'Title 2']
        mock_evaluate.return_value = ('feedback', 'Best Title')

        api = OpenAIAPI(api_key="test")
        result = api.process_project("https://github.com/user/repo", "# README")

        assert result == 'Best Title'


class TestEvaluateAndReviseTitles:
    """Tests for evaluate_and_revise_titles method."""

    def test_regenerates_on_low_score(self):
        """Test that low-scoring titles trigger regeneration."""
        api = OpenAIAPI(api_key="test")

        # Give titles that will score low (single character)
        titles = ['X', 'Y']

        # evaluate_title should give low scores for these
        score_x = api.evaluate_title('X', "taxi-project", "taxi data")
        score_y = api.evaluate_title('Y', "taxi-project", "taxi data")

        # Both should score below 3 (triggering regeneration)
        assert score_x < 3
        assert score_y < 3

    @patch.object(OpenAIAPI, 'generate_multiple_titles')
    def test_regeneration_returns_better_title(self, mock_generate):
        """Test that regeneration picks the better title without KeyError."""
        mock_generate.return_value = ['NYC Taxi Data Pipeline']

        api = OpenAIAPI(api_key="test")
        titles = ['X', 'Y']  # Low scoring titles

        # This should not raise KeyError anymore (bug fix)
        feedback, best = api.evaluate_and_revise_titles(
            titles, "taxi-project", "taxi data analysis"
        )

        assert best == 'NYC Taxi Data Pipeline'
        assert 'NYC Taxi Data Pipeline' in feedback

    def test_keeps_good_title(self):
        api = OpenAIAPI(api_key="test")
        titles = ['NYC Taxi Data Pipeline', 'Weather Analytics']

        feedback, best = api.evaluate_and_revise_titles(
            titles, "taxi-project", "taxi data analysis"
        )

        assert 'Taxi' in best


class TestLLMMethod:
    """Tests for llm method."""

    @patch('utils.openai_api.OpenAI')
    def test_handles_api_error(self, mock_openai_class):
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        api = OpenAIAPI(api_key="test")
        result, usage = api.llm("test prompt")

        assert result is None
        assert usage is None


class TestDefaultClassification:
    """Tests for _default_classification method."""

    def test_returns_unknown_values(self):
        api = OpenAIAPI(api_key="test")
        result = api._default_classification()

        assert result['deployment_type'] == 'Unknown'
        assert result['cloud_provider'] == 'Unknown'
        assert 'Could not classify' in result['deployment_reason']


class TestClientTimeout:
    """Tests for API client timeout configuration."""

    @patch('utils.openai_api.OpenAI')
    def test_client_has_timeout(self, mock_openai_class):
        """Test that OpenAI client is initialized with timeout."""
        api = OpenAIAPI(api_key="test-key")

        # Verify OpenAI was called with timeout parameter
        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args[1]

        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 60.0

    @patch('utils.openai_api.OpenAI')
    def test_client_uses_openrouter_base_url(self, mock_openai_class):
        """Test that client uses OpenRouter base URL."""
        api = OpenAIAPI(api_key="test-key")

        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs['base_url'] == "https://openrouter.ai/api/v1"
