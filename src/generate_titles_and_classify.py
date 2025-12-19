"""
Unified pipeline: Generate titles AND classify deployment/cloud using multi-file context.

This combines:
- Multi-file fetching (simplified approach from ZoomJudge)
- Existing title generation logic
- LLM-based deployment/cloud classification
- PARALLEL PROCESSING for 5-10x speedup

Run: python -m src.generate_titles_and_classify
"""

import os
import time
import logging
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

from utils.openai_api import OpenAIAPI
from utils.csv_handler import CSVHandler, fix_mojibake
from utils.repo_analyzer import RepoAnalyzer

from .config import get_config

load_dotenv()


# Check for required environment variables early
def _check_env_vars():
    missing = []
    if not os.environ.get("MY_GITHUB_TOKEN"):
        missing.append("MY_GITHUB_TOKEN")
    if not os.environ.get("OPENROUTER_API_KEY"):
        missing.append("OPENROUTER_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them before running: export MY_GITHUB_TOKEN='...' OPENROUTER_API_KEY='...'"
        )


# Suppress noisy logging - only show progress bar
logging.basicConfig(
    filename='unified_pipeline.log',
    level=logging.WARNING,  # Changed from INFO to WARNING
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Silence httpx and other noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("utils.repo_analyzer").setLevel(logging.WARNING)


# Thread-safe counter
class Counter:
    def __init__(self):
        self.success = 0
        self.skip = 0
        self.error = 0
        self._lock = Lock()

    def inc_success(self):
        with self._lock:
            self.success += 1

    def inc_skip(self):
        with self._lock:
            self.skip += 1

    def inc_error(self):
        with self._lock:
            self.error += 1


# Lock for thread-safe DataFrame updates
_df_lock = Lock()


def truncate_text(text, max_characters=3500):
    return text[:max_characters]


def process_single_project(args):
    """
    Process a single project - designed for parallel execution.

    Returns:
        tuple: (index, result_dict) where result_dict contains all fields to update
    """
    index, row, repo_analyzer, openai_api, valid_deployment_types = args
    project_url = row['project_url']

    result = {
        'project_title': row.get('project_title'),
        'Deployment Type': row.get('Deployment Type'),
        'Reason': row.get('Reason'),
        'Cloud': row.get('Cloud'),
        'status': 'success',
    }

    # Check if already processed (skip if both title and deployment are valid, non-Unknown values)
    existing_title = row.get('project_title')
    existing_deployment = row.get('Deployment Type')
    if (
        pd.notnull(existing_title)
        and existing_title != 'Unknown'
        and existing_title != 'Error'
        and pd.notnull(existing_deployment)
        and existing_deployment != 'Unknown'
        and existing_deployment != 'Error'
    ):
        result['status'] = 'skip'
        return index, result

    try:
        # Step 1: Fetch multi-file context
        repo_data = repo_analyzer.analyze_repo(project_url)
        files_content = repo_data.get('files', {})

        if not files_content:
            logger.warning(f"No files fetched for {project_url}")
            result['project_title'] = "Unknown"
            result['Deployment Type'] = "Unknown"
            result['Reason'] = "No files fetched"
            result['Cloud'] = "Unknown"
            result['status'] = 'skip'
            return index, result

        # Step 2: Classify deployment type and cloud FIRST (needed for title generation)
        deployment_type = row.get('Deployment Type')
        if pd.isnull(deployment_type) or deployment_type == 'Unknown':
            classification = openai_api.classify_deployment_and_cloud(
                project_url, files_content, valid_deployment_types
            )

            deployment_type = classification['deployment_type']
            result['Deployment Type'] = deployment_type
            result['Reason'] = classification['deployment_reason']
            result['Cloud'] = classification['cloud_provider']

        # Step 3: Generate title using deployment type context
        if pd.isnull(row.get('project_title')):
            combined_content = ""
            for filepath, content in files_content.items():
                combined_content += f"\n=== {filepath} ===\n"
                combined_content += content[:2000]

            combined_content = truncate_text(combined_content, max_characters=6000)

            if combined_content:
                summary = openai_api.generate_summary(combined_content)
                if summary:
                    # Pass deployment_type to avoid "Real-Time" in Batch titles
                    titles = openai_api.generate_multiple_titles(
                        project_url, summary, deployment_type=deployment_type
                    )
                    if titles:
                        _, best_title = openai_api.evaluate_and_revise_titles(
                            titles, project_url, summary
                        )
                        result['project_title'] = best_title
                    else:
                        result['project_title'] = "Unknown"
                else:
                    result['project_title'] = "Unknown"
            else:
                result['project_title'] = "Unknown"

        result['status'] = 'success'
        return index, result

    except Exception as e:
        logger.error(f"Error processing {project_url}: {e}")
        result['project_title'] = result.get('project_title') or "Error"
        result['Deployment Type'] = "Error"
        result['Reason'] = str(e)[:100]
        result['Cloud'] = "Error"
        result['status'] = 'error'
        return index, result


def main():
    _check_env_vars()

    config = get_config()
    cleaned_csv_path = config['cleaned_csv_path']
    output_csv_path = config.get('deploy_csv_path', 'Data/data.csv')

    # Parallel workers - be careful with API rate limits
    # GitHub: 5000 req/hour, OpenRouter: varies by model
    max_workers = config.get('max_workers', 5)

    csv_handler = CSVHandler(cleaned_csv_path)

    # Apply limit if specified
    limit = config.get('limit', 0)
    if limit > 0:
        csv_handler.df = csv_handler.df.head(limit)
        print(f"⚠️  Limited to {limit} projects for testing")

    # Initialize columns
    for col in ['project_title', 'Deployment Type', 'Reason', 'Cloud']:
        if col not in csv_handler.df.columns:
            csv_handler.df[col] = None

    # Initialize APIs (these are thread-safe for read operations)
    repo_analyzer = RepoAnalyzer(os.environ.get('MY_GITHUB_TOKEN'))
    openai_api = OpenAIAPI(os.environ.get('OPENROUTER_API_KEY'))

    total = len(csv_handler.df)
    print(f"🚀 Processing {total} projects with {max_workers} parallel workers...")
    print("=" * 60)

    start_time = time.time()
    counter = Counter()

    # Get valid deployment types for this course
    valid_deployment_types = config.get(
        'valid_deployment_types', ['Batch', 'Streaming', 'Web Service']
    )
    print(f"📋 Valid deployment types for {config['course']}: {valid_deployment_types}")

    # Prepare work items
    work_items = [
        (idx, row, repo_analyzer, openai_api, valid_deployment_types)
        for idx, row in csv_handler.df.iterrows()
    ]

    # Process in parallel with progress bar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_project, item): item[0]
            for item in work_items
        }

        with tqdm(total=total, desc="Processing", unit="project") as pbar:
            for future in as_completed(futures):
                try:
                    index, result = future.result()

                    # Update dataframe with lock for thread safety
                    with _df_lock:
                        csv_handler.df.at[index, 'project_title'] = result[
                            'project_title'
                        ]
                        csv_handler.df.at[index, 'Deployment Type'] = result[
                            'Deployment Type'
                        ]
                        csv_handler.df.at[index, 'Reason'] = result['Reason']
                        csv_handler.df.at[index, 'Cloud'] = result['Cloud']

                    # Update counters
                    if result['status'] == 'success':
                        counter.inc_success()
                    elif result['status'] == 'skip':
                        counter.inc_skip()
                    else:
                        counter.inc_error()

                    pbar.set_postfix(
                        {
                            "✓": counter.success,
                            "skip": counter.skip,
                            "err": counter.error,
                        },
                        refresh=True,
                    )
                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Future failed: {e}")
                    counter.inc_error()
                    pbar.update(1)

    elapsed = time.time() - start_time

    # Fix encoding issues (mojibake) in text columns using utility function
    csv_handler.fix_mojibake_columns(['project_title', 'Reason'])

    # Clean up titles - remove unwanted prefixes and quotes
    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        '"', '', regex=False
    )
    csv_handler.df['project_title'] = csv_handler.df['project_title'].str.replace(
        'Title: ', '', regex=False
    )

    # Save results
    csv_handler.save(output_csv_path)

    print("\n" + "=" * 60)
    rate = total / elapsed if elapsed > 0 else 0
    print(f"✅ Completed in {elapsed:.1f}s ({rate:.1f} projects/sec)")
    print(
        f"   Success: {counter.success} | Skipped: {counter.skip} | Errors: {counter.error}"
    )
    print(f"📊 Results saved to: {output_csv_path}")

    # Print summary stats
    print("\n📈 Summary:")
    print(
        f"   Deployment Types: {csv_handler.df['Deployment Type'].value_counts().to_dict()}"
    )
    print(f"   Cloud Providers: {csv_handler.df['Cloud'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
