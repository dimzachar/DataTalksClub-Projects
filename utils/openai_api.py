import os
import re
import time

from openai import OpenAI
from tqdm import tqdm


class OpenAIAPI:
    """
    LLM API client using OpenRouter (compatible with OpenAI SDK).
    Uses a free OpenRouter model by default.
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            timeout=60.0,  # 60 second timeout for API calls
        )
        # Free models with fallback order (5 models for better throughput)
        self.default_model = os.environ.get("DEFAULT_MODEL", "openai/gpt-oss-120b:free")
        self.fallback_models = [
            self.default_model,
            "openai/gpt-oss-20b:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-3-27b-it:free",
            "google/gemma-3-12b-it:free",
        ]

    def build_prompt(self, project_url, summary, deployment_type=None):
        # Determine what tech terms are allowed based on deployment type
        tech_guidance = ""
        if deployment_type:
            if 'streaming' in deployment_type.lower():
                tech_guidance = "This is a STREAMING project - you may use 'Real-Time' or 'Streaming' if appropriate."
            else:
                tech_guidance = "This is a BATCH project - do NOT use 'Real-Time', 'Streaming', or 'Live' in titles."

        prompt_template = """
Generate 5 unique titles for this data engineering project. Guidelines:

1. Focus on WHAT the project does (domain/data), not course names or repo structure.
2. Titles should be 3-5 words, descriptive of the actual functionality.
3. NEVER include: "zoomcamp", "bootcamp", "final project", "course", "curriculum", "assignment", "homework".
4. Focus on the DATA DOMAIN (e.g., "NYC Taxi Analytics", "Weather Data Pipeline", "Stock Market Dashboard").
5. Do NOT invent or assume specific technologies (Kafka, Spark, etc.) - only mention tech if it's clearly in the summary.
6. Prefer specific domain nouns from the summary (for example: air quality, taxi, sales, weather, trips).
7. Avoid generic/vague titles like "Cloud Storage Data Integration", "Data Platform Pipeline", or "Data Processing System".
8. Keep title-case style and avoid filler words.

{tech_guidance}

BAD titles:
- "DE Zoomcamp 2025 Project" (generic)
- "Kafka-Powered Data Pipeline" (inventing tech not mentioned)
- "Cloud Storage Data Integration" (generic and vague)

GOOD titles (domain-specific):
- "NYC Taxi Fare Analytics"
- "Weather Data Pipeline"
- "E-commerce Sales Dashboard"

Project URL: {url}
Project Summary: {summary}

Generate 5 distinct domain-focused titles, each on a new line:
""".strip()
        return prompt_template.format(
            url=project_url, summary=summary, tech_guidance=tech_guidance
        )

    def build_prompt_legacy(self, project_url, summary):
        """Legacy method for backward compatibility."""
        return self.build_prompt(project_url, summary, deployment_type=None)

    def llm(self, prompt, model=None, max_tokens=150, temperature=0, max_retries=5):
        # Build model queue: requested model first, then fallbacks (deduped)
        requested = model or self.default_model
        model_queue = [requested] + [m for m in self.fallback_models if m != requested]

        for attempt in range(max_retries):
            current_model = model_queue[attempt % len(model_queue)]
            try:
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://github.com/DataTalksClub",
                        "X-Title": "DataTalksClub Projects",
                    },
                    model=current_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if not response.choices:
                    raise ValueError("Empty choices in response")
                content = response.choices[0].message.content
                return content, response.usage
            except Exception as e:
                error_str = str(e)
                is_last = attempt == max_retries - 1

                if "429" in error_str:
                    # Extract retry-after if present, else back off exponentially
                    wait = 60 * (2 ** min(attempt, 3))
                    next_model = model_queue[(attempt + 1) % len(model_queue)]
                    tqdm.write(
                        f"⚠️  Rate limited on {current_model} (attempt {attempt+1}/{max_retries})"
                        f" — waiting {wait}s, then trying {next_model}"
                    )
                    if not is_last:
                        time.sleep(wait)
                elif "404" in error_str:
                    next_model = model_queue[(attempt + 1) % len(model_queue)]
                    tqdm.write(
                        f"❌ Model not found: {current_model} — switching to {next_model}"
                    )
                    if not is_last:
                        time.sleep(2)
                else:
                    tqdm.write(f"❌ LLM error on {current_model} (attempt {attempt+1}/{max_retries}): {error_str[:120]}")
                    if not is_last:
                        time.sleep(5)

                if is_last:
                    tqdm.write(f"💀 All {max_retries} attempts failed for model queue {model_queue}")
                    return None, None
        return None, None

    def generate_summary(self, content):
        prompt_summary = f"Summarize the following GitHub project content in two sentences, focusing on its main purpose and key features:\n{content}"
        summary, _ = self.llm(prompt_summary, max_tokens=100)
        return summary.strip() if summary else ""

    def generate_multiple_titles(self, project_url, summary, deployment_type=None):
        title_prompt = self.build_prompt(project_url, summary, deployment_type)
        titles, _ = self.llm(title_prompt, max_tokens=150)
        if titles:
            titles_list = [
                re.sub(
                    r'^[-\d]+\.\s*', '', title.strip()
                )  # Only remove leading list markers like "1. " or "- "
                for title in titles.split('\n')
                if title.strip()
            ]
            return list(set(filter(None, titles_list)))
        return []

    def evaluate_title(self, title, project_url, summary):
        score = 0
        word_count = len(title.split())

        if 3 <= word_count <= 5:
            score += 2
        elif word_count < 3 or word_count > 5:
            score -= 1

        generic_core = {
            'cloud',
            'integration',
            'processing',
            'system',
            'storage',
        }
        keywords = [
            word
            for word in re.findall(r'\w+', project_url.lower() + ' ' + summary.lower())
            if word not in generic_core and len(word) > 2
        ]
        for word in title.lower().split():
            if word in keywords:
                score += 1

        generic_terms = [
            'smart',
            'intelligent',
            'assistant',
            'hub',
            'companion',
            'generic',
            'solution',
            'system',
        ]
        for term in generic_terms:
            if term in title.lower():
                score -= 1

        title_words = re.findall(r'\w+', title.lower())
        non_generic_words = [w for w in title_words if w not in generic_core]
        if len(non_generic_words) < 2:
            score -= 2
        if title_words and title_words[0] in generic_core:
            score -= 1

        if ':' in title or '-' in title:
            score += 1

        return score

    def evaluate_and_revise_titles(self, titles, project_url, summary):
        scores = {
            title: self.evaluate_title(title, project_url, summary) for title in titles
        }
        best_title = max(scores, key=scores.get)

        if scores[best_title] < 3:
            new_titles = self.generate_multiple_titles(project_url, summary)
            new_scores = {
                title: self.evaluate_title(title, project_url, summary)
                for title in new_titles
            }
            combined_scores = {**scores, **new_scores}
            best_title = max(combined_scores, key=combined_scores.get)
            scores = combined_scores  # Update scores to include new titles

        feedback = (
            f"The best title is '{best_title}' with a score of {scores[best_title]}."
        )
        return feedback, best_title

    def process_project(self, project_url, content):
        summary = self.generate_summary(content)
        titles = self.generate_multiple_titles(project_url, summary)
        feedback, best_title = self.evaluate_and_revise_titles(
            titles, project_url, summary
        )
        return best_title

    def classify_deployment_and_cloud(
        self, project_url: str, files_content: dict, valid_deployment_types: list = None
    ) -> dict:
        """
        Classify deployment type and cloud provider using multi-file context.

        Args:
            project_url: GitHub repository URL
            files_content: dict of {filepath: content} from RepoAnalyzer
            valid_deployment_types: list of valid types for this course (e.g., ['Batch', 'Streaming'])

        Returns:
            dict with deployment_type, deployment_reason, cloud_provider, cloud_reason
        """
        # Default valid types if not specified
        if valid_deployment_types is None:
            valid_deployment_types = ['Batch', 'Streaming', 'Web Service']

        # Format files for prompt
        formatted = ""
        for filepath, content in files_content.items():
            truncated = content[:3000] if len(content) > 3000 else content
            formatted += f"\n--- {filepath} ---\n{truncated}\n"

        if len(formatted) > 12000:
            formatted = formatted[:12000] + "\n[truncated...]"

        # Build deployment type options dynamically
        type_descriptions = {
            'Batch': 'Batch: Uses workflow orchestrators (Airflow, Prefect, Kestra, Mage) to run scheduled ETL jobs. Data is pulled periodically, transformed, loaded to warehouse. Look for: DAGs, flow.yml, scheduled tasks, dbt runs.',
            'Streaming': 'Streaming: Uses message brokers (Kafka, Kinesis, Redpanda, Flink) where data flows continuously. Look for: kafka topics, producers/consumers, flink jobs, real-time processing.',
            'Web Service': 'Web Service: Serves ML models or results via API (Flask, FastAPI, BentoML, Streamlit for ML inference).',
        }

        type_options = '\n   - '.join(
            [type_descriptions.get(t, t) for t in valid_deployment_types]
        )
        valid_types_str = ', '.join(valid_deployment_types)

        prompt = f"""Analyze this GitHub repository and classify it.

REPOSITORY URL: {project_url}

REPOSITORY FILES:
{formatted}

Based on the ACTUAL CODE and configuration files, determine:

1. DEPLOYMENT TYPE (choose from: {valid_types_str}):
   - {type_options}
   - Unknown: Cannot determine from code

   RULES:
   - ONLY use these types: {valid_types_str}, Unknown
   - If project has BOTH streaming AND batch components, list BOTH: "Batch, Streaming"
   - Streamlit/Gradio dashboards for visualization are NOT "Streaming" - they are visualization layers

2. CLOUD PROVIDER (choose ONE):
   - GCP: BigQuery, Cloud Run, Dataflow, GCS, Vertex AI, Terraform google provider
   - AWS: S3, Lambda, Redshift, Glue, EMR, Terraform aws provider
   - Azure: Azure Data Factory, Synapse, Blob Storage, Terraform azurerm provider
   - Other: Different cloud or self-hosted
   - Unknown: Cannot determine from code

Respond ONLY in this exact format:
DEPLOYMENT: <type or types comma-separated>
DEPLOYMENT_REASON: <brief reason>
CLOUD: <provider>
CLOUD_REASON: <brief reason>"""

        try:
            response, _ = self.llm(prompt, max_tokens=200)
            if not response:
                return self._default_classification("LLM returned no response")

            return self._parse_classification_response(response)
        except Exception as e:
            print(f"Classification error: {e}")
            return self._default_classification(str(e)[:100])

    def _parse_classification_response(self, response: str) -> dict:
        """Parse the classification response."""
        result = {
            'deployment_type': 'Unknown',
            'deployment_reason': 'Unknown',
            'cloud_provider': 'Unknown',
            'cloud_reason': 'Unknown',
        }

        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('DEPLOYMENT:'):
                value = line.replace('DEPLOYMENT:', '').strip()
                value_lower = value.lower()

                # Check for valid types
                types = []
                if 'batch' in value_lower:
                    types.append('Batch')
                if 'stream' in value_lower:
                    types.append('Streaming')
                if 'web' in value_lower or 'service' in value_lower:
                    types.append('Web Service')

                if types:
                    result['deployment_type'] = ', '.join(types)
                else:
                    result['deployment_type'] = 'Unknown'
            elif line.startswith('DEPLOYMENT_REASON:'):
                result['deployment_reason'] = line.replace(
                    'DEPLOYMENT_REASON:', ''
                ).strip()
            elif line.startswith('CLOUD:'):
                value = line.replace('CLOUD:', '').strip()
                value_lower = value.lower()
                if 'gcp' in value_lower or 'google' in value_lower:
                    result['cloud_provider'] = 'GCP'
                elif 'aws' in value_lower or 'amazon' in value_lower:
                    result['cloud_provider'] = 'AWS'
                elif 'azure' in value_lower:
                    result['cloud_provider'] = 'Azure'
                elif 'unknown' in value_lower:
                    result['cloud_provider'] = 'Unknown'
                else:
                    result['cloud_provider'] = value
            elif line.startswith('CLOUD_REASON:'):
                result['cloud_reason'] = line.replace('CLOUD_REASON:', '').strip()

        return result

    def _default_classification(self, reason: str = "Could not classify") -> dict:
        """Return default classification when LLM fails."""
        return {
            'deployment_type': 'Unknown',
            'deployment_reason': reason,
            'cloud_provider': 'Unknown',
            'cloud_reason': reason,
        }
