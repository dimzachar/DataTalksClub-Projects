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
    if len(args) == 6:
        (
            index,
            row,
            repo_analyzer,
            openai_api,
            valid_deployment_types,
            force_reprocess,
        ) = args
    else:
        index, row, repo_analyzer, openai_api, valid_deployment_types = args
        force_reprocess = False
    project_url = row['project_url']

    result = {
        'project_title': row.get('project_title'),
        'Deployment Type': row.get('Deployment Type'),
        'Reason': row.get('Reason'),
        'Cloud': row.get('Cloud'),
        'readme_path': None,
        'readme_preview': None,
        'status': 'success',
    }

    # Permanent skip: repo previously returned 404 (deleted/private)
    existing_reason = row.get('Reason', '')
    if isinstance(existing_reason, str) and existing_reason.startswith('404:'):
        result['status'] = 'skip'
        return index, result

    # Check if already processed (skip if both title and deployment are valid, non-Unknown values)
    existing_title = row.get('project_title')
    existing_deployment = row.get('Deployment Type')
    title_valid = (
        pd.notnull(existing_title)
        and isinstance(existing_title, str)
        and existing_title.strip().lower() not in ('unknown', 'error')
    )
    dep_valid = (
        pd.notnull(existing_deployment)
        and isinstance(existing_deployment, str)
        and existing_deployment.strip().lower() not in ('unknown', 'error')
    )
    if not force_reprocess and title_valid and dep_valid:
        result['status'] = 'skip'
        return index, result

    try:
        # Step 1: Fetch multi-file context
        repo_data = repo_analyzer.analyze_repo(project_url)
        files_content = repo_data.get('files', {})

        if repo_data.get('not_found'):
            logger.warning(f"Repo not found (404): {project_url}")
            result['project_title'] = "Unknown"
            result['Deployment Type'] = "Unknown"
            result['Reason'] = "404: Repository not found (may be deleted or private)"
            result['Cloud'] = "Unknown"
            result['status'] = 'skip'
            return index, result

        if not files_content:
            logger.warning(f"No files fetched for {project_url}")
            result['project_title'] = "Unknown"
            result['Deployment Type'] = "Unknown"
            result['Reason'] = "No files fetched"
            result['Cloud'] = "Unknown"
            result['status'] = 'skip'
            return index, result

        # In single-project debug mode, expose which README was fetched.
        if force_reprocess:
            readme_candidates = []
            for path, content in files_content.items():
                filename = path.split('/')[-1].lower()
                if filename in ('readme.md', 'readme'):
                    readme_candidates.append((path, content))

            if readme_candidates:
                # Prefer top-level README for quick verification in logs.
                readme_candidates.sort(key=lambda item: item[0].count('/'))
                chosen_path, chosen_content = readme_candidates[0]
                preview = chosen_content[:700].replace('\n', ' ').strip()
                result['readme_path'] = chosen_path
                result['readme_preview'] = preview

        # Step 2: Classify deployment type and cloud FIRST (needed for title generation)
        deployment_type = row.get('Deployment Type')
        if (
            force_reprocess
            or pd.isnull(deployment_type)
            or (isinstance(deployment_type, str) and deployment_type.strip().lower() == 'unknown')
        ):
            classification = openai_api.classify_deployment_and_cloud(
                project_url, files_content, valid_deployment_types
            )

            deployment_type = classification['deployment_type']
            result['Deployment Type'] = deployment_type
            result['Reason'] = classification['deployment_reason']
            result['Cloud'] = classification['cloud_provider']

        # Step 3: Generate title using deployment type context
        existing_title = row.get('project_title')
        existing_reason = row.get('Reason', '')
        title_needs_gen = (
            force_reprocess
            or pd.isnull(existing_title)
            or (isinstance(existing_title, str) and existing_title.strip().lower() in ('unknown', 'error'))
            or (isinstance(existing_reason, str) and 'no files fetched' in existing_reason.lower())
        )
        if title_needs_gen:
            combined_content = ""
            for filepath, content in files_content.items():
                combined_content += f"\n=== {filepath} ===\n"
                combined_content += content[:2000]

            combined_content = truncate_text(combined_content, max_characters=6000)

            if combined_content:
                summary = openai_api.generate_summary(combined_content)
                if summary:
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
                        result['Reason'] = result.get('Reason', '') + " | Title: LLM returned no titles"
                else:
                    result['project_title'] = "Unknown"
                    result['Reason'] = result.get('Reason', '') + " | Title: LLM summary failed"
            else:
                result['project_title'] = "Unknown"
                result['Reason'] = result.get('Reason', '') + " | Title: No content to summarize"

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


def run_parallel(work_items, max_workers, csv_handler, counter, failed_urls):
    """Run work_items in parallel, update csv_handler.df, and collect failed URLs."""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_project, item): item[0]
            for item in work_items
        }

        with tqdm(total=len(work_items), desc="Processing", unit="project") as pbar:
            for future in as_completed(futures):
                try:
                    index, result = future.result()

                    with _df_lock:
                        csv_handler.df.at[index, 'project_title'] = result['project_title']
                        csv_handler.df.at[index, 'Deployment Type'] = result['Deployment Type']
                        csv_handler.df.at[index, 'Reason'] = result['Reason']
                        csv_handler.df.at[index, 'Cloud'] = result['Cloud']

                    if result['status'] == 'success':
                        counter.inc_success()
                    elif result['status'] == 'skip':
                        counter.inc_skip()
                    else:
                        counter.inc_error()
                        with _df_lock:
                            url = csv_handler.df.at[index, 'project_url']
                        failed_urls.append((index, url))

                    pbar.set_postfix(
                        {"✓": counter.success, "skip": counter.skip, "err": counter.error},
                        refresh=True,
                    )
                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Future failed: {e}")
                    counter.inc_error()
                    pbar.update(1)


def main():
    _check_env_vars()

    config = get_config()
    cleaned_csv_path = config['cleaned_csv_path']
    output_csv_path = config.get('deploy_csv_path', 'Data/data.csv')

    # Parallel workers - be careful with API rate limits
    # GitHub: 5000 req/hour, OpenRouter: varies by model
    max_workers = config.get('max_workers', 5)

    csv_handler = CSVHandler(cleaned_csv_path)

    # Preserve existing enrichment from data.csv (if present), so targeted reruns
    # update rows instead of replacing the whole output with a filtered subset.
    result_columns = ['project_title', 'Deployment Type', 'Reason', 'Cloud']
    if os.path.exists(output_csv_path):
        try:
            existing_df = pd.read_csv(output_csv_path)
            if 'project_url' in existing_df.columns:
                existing_df = existing_df.drop_duplicates(subset=['project_url'])
                existing_df = existing_df.set_index('project_url')
                for col in result_columns:
                    if col in existing_df.columns:
                        csv_handler.df[col] = csv_handler.df['project_url'].map(
                            existing_df[col]
                        )
        except Exception as e:
            logger.warning(f"Could not load existing output CSV {output_csv_path}: {e}")

    # Optional: process just one repo URL
    old_target_row = None
    project_url = config.get('project_url')
    process_df = csv_handler.df
    if project_url:
        normalized_target = project_url.rstrip('/')
        normalized_series = csv_handler.df['project_url'].astype(str).str.rstrip('/')
        process_df = csv_handler.df[normalized_series == normalized_target]
        if process_df.empty:
            raise ValueError(
                f"Project URL not found in {cleaned_csv_path}: {project_url}"
            )
        print(f"🎯 Filtered to project: {project_url}")
        print("🔁 Force reprocessing enabled for this project URL")
        output_columns = ['project_url', 'project_title', 'Deployment Type', 'Reason', 'Cloud']
        available_columns = [c for c in output_columns if c in csv_handler.df.columns]
        old_target_row = (
            csv_handler.df.loc[normalized_series == normalized_target, available_columns]
            .iloc[0]
            .to_dict()
        )

    # Apply limit if specified
    limit = config.get('limit', 0)
    if limit > 0:
        process_df = process_df.head(limit)
        print(f"⚠️  Limited to {limit} projects for testing")

    # Initialize columns
    for col in result_columns:
        if col not in csv_handler.df.columns:
            csv_handler.df[col] = None

    # Initialize APIs (these are thread-safe for read operations)
    repo_analyzer = RepoAnalyzer(os.environ.get('MY_GITHUB_TOKEN'))
    openai_api = OpenAIAPI(os.environ.get('OPENROUTER_API_KEY'))

    total = len(process_df)
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
        (
            idx,
            row,
            repo_analyzer,
            openai_api,
            valid_deployment_types,
            bool(project_url),
        )
        for idx, row in process_df.iterrows()
    ]

    failed_urls = []

    # Process in parallel with progress bar
    run_parallel(work_items, max_workers, csv_handler, counter, failed_urls)

    # Retry failed projects once
    if failed_urls:
        print(f"\n⚠️  Retrying {len(failed_urls)} failed projects...")
        retry_items = [
            (
                idx,
                csv_handler.df.loc[idx],
                repo_analyzer,
                openai_api,
                valid_deployment_types,
                True,  # force_reprocess
            )
            for idx, _ in failed_urls
        ]
        retry_counter = Counter()
        retry_failed = []
        run_parallel(retry_items, max_workers, csv_handler, retry_counter, retry_failed)
        counter.success += retry_counter.success
        counter.error = len(retry_failed)

        if retry_failed:
            print(f"\n❌ {len(retry_failed)} projects still failed after retry:")
            for _, url in retry_failed:
                print(f"   {url}")

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

    if project_url:
        normalized_series = csv_handler.df['project_url'].astype(str).str.rstrip('/')
        normalized_target = project_url.rstrip('/')
        target_rows = csv_handler.df[normalized_series == normalized_target]
        if not target_rows.empty:
            output_columns = ['project_url', 'project_title', 'Deployment Type', 'Reason', 'Cloud']
            available_columns = [c for c in output_columns if c in csv_handler.df.columns]
            target_row = target_rows.iloc[0][available_columns].to_dict()
            print("\n🎯 Single project result:")
            print(f"   URL: {project_url}")
            print(f"   Title: {target_row.get('project_title', 'Unknown')}")
            print(f"   Deployment: {target_row.get('Deployment Type', 'Unknown')}")
            print(f"   Cloud: {target_row.get('Cloud', 'Unknown')}")
            debug_result = None

            if debug_result:
                if debug_result.get('readme_path'):
                    print("\n📄 README preview (truncated):")
                    print(f"   Path: {debug_result['readme_path']}")
                    print(f"   Text: {debug_result.get('readme_preview', '')}")
                else:
                    print("\n📄 README preview (truncated):")
                    print("   README file not found in fetched key files.")
            if old_target_row is not None:
                print("\n📝 Full row diff:")
                print(f"   OLD: {old_target_row}")
                print(f"   NEW: {target_row}")

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
