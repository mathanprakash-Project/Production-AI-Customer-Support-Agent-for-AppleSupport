"""
Main orchestrator script for the TweetSupport AI Support Agent project pipeline.
Runs the full end-to-end process: data download -> preprocessing -> intent discovery -> index building -> evaluation.
"""

import argparse
import logging
import time
import sys
from config import BRAND, SUBSAMPLE_SIZE, ensure_directories
import os
import json
from pathlib import Path

from config import BRAND, SUBSAMPLE_SIZE, PROCESSED_DIR, RESULTS_DIR, ensure_directories

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="TweetSupport AI Support Agent Pipeline")
    parser.add_argument(
        "--smoke-test", 
        action="store_true", 
        "--smoke-test",
        action="store_true",
        help="Run the pipeline on a tiny subsample for fast testing (100 tweets)."
    )
    parser.add_argument(
        "--brand", 
        type=str, 
        "--brand",
        type=str,
        default=BRAND,
        help="Brand to analyze (overrides default in config.py)."
    )
    parser.add_argument(
        "--skip-download", 
        action="store_true", 
        "--skip-download",
        action="store_true",
        help="Skip the data download step."
    )
    parser.add_argument(
        "--skip-intents",
        action="store_true",
        help="Skip intent discovery (use existing taxonomy.json)."
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip evaluation step."
    )
    return parser.parse_args()


def run_step(step_name, func, *args, **kwargs):
    """Run a pipeline step with timing and error handling."""
    logger.info(f"--- Starting: {step_name} ---")
    start_time = time.time()
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"--- Completed: {step_name} in {elapsed:.2f} seconds ---\n")
        return result
    except Exception as e:
        logger.error(f"Error during {step_name}: {e}", exc_info=True)
        sys.exit(1)

# Dummy stubs for pipeline stages until they are implemented
def download_data():
    logger.info("Downloading dataset...")

def step_download():
    """Download the dataset from Kaggle."""
    from data.download import download_dataset
    csv_path = download_dataset(str(Path("data")))
    return csv_path


def step_preprocess(brand: str, subsample_size: int) -> str:
    """Preprocess the raw data into threads."""
    from data.preprocess import run_preprocessing
    
def preprocess_data(brand, subsample_size):
    logger.info(f"Preprocessing data for brand: {brand} with size: {subsample_size}...")
    # Find the CSV file
    csv_path = None
    data_dir = Path("data")
    for f in data_dir.rglob("*.csv"):
        if "twcs" in f.name.lower():
            csv_path = str(f)
            break
    
    if not csv_path:
        # Try kagglehub cache
        import kagglehub
        csv_path = kagglehub.dataset_download("thoughtvector/customer-support-on-twitter")
        csv_files = list(Path(csv_path).rglob("*.csv"))
        if csv_files:
            csv_path = str(csv_files[0])
        else:
            raise FileNotFoundError("Could not find twcs.csv. Run without --skip-download first.")
    
    threads_path = run_preprocessing(
        csv_path=csv_path,
        brand=brand,
        subsample_size=subsample_size,
        output_dir=str(PROCESSED_DIR)
    )
    return threads_path

def discover_intents():
    logger.info("Discovering intents...")

def build_retriever_index():
    logger.info("Building retriever index...")
def step_discover_intents(threads_path: str) -> dict:
    """Discover intent taxonomy from the data."""
    from intent.discover import discover_intents, load_taxonomy
    
    taxonomy_path = Path("intent") / "taxonomy.json"
    if taxonomy_path.exists():
        logger.info("Taxonomy already exists. Loading existing taxonomy.")
        return load_taxonomy(str(taxonomy_path))
    
    # Load first customer messages from threads
    messages = []
    with open(threads_path, 'r', encoding='utf-8') as f:
        for line in f:
            thread = json.loads(line)
            msg = thread.get("first_customer_message", "")
            if msg and len(msg.strip()) > 10:
                messages.append(msg)
    
    logger.info(f"Discovering intents from {len(messages)} customer messages...")
    taxonomy = discover_intents(messages)
    return taxonomy

def run_evaluation():
    logger.info("Running evaluation on golden set...")

def step_build_golden_set(threads_path: str, taxonomy: dict):
    """Build the golden evaluation set."""
    from eval.golden_set.build_golden_set import build_golden_set
    from intent.classifier import LLMClassifier
    
    golden_set_path = Path("eval") / "golden_set" / "golden_set.jsonl"
    if golden_set_path.exists():
        logger.info("Golden set already exists. Skipping.")
        return str(golden_set_path)
    
    # Load threads
    threads = []
    with open(threads_path, 'r', encoding='utf-8') as f:
        for line in f:
            threads.append(json.loads(line))
    
    classifier = LLMClassifier(taxonomy=taxonomy)
    build_golden_set(threads, classifier, output_path=str(golden_set_path))
    return str(golden_set_path)


def step_evaluate(golden_set_path: str, threads_path: str):
    """Run the evaluation harness."""
    from eval.run_eval import run_full_evaluation
    from agent.pipeline import AgentPipeline
    
    pipeline = AgentPipeline(threads_path=threads_path)
    results = run_full_evaluation(
        golden_set_path=golden_set_path,
        agent_pipeline=pipeline,
        output_dir=str(RESULTS_DIR)
    )
    return results


def main():
    args = parse_args()
    

    # Override settings if smoke test
    active_brand = args.brand
    active_subsample_size = 100 if args.smoke_test else SUBSAMPLE_SIZE
    
    logger.info(f"Initializing pipeline for brand: {active_brand}")

    logger.info(f"╔══════════════════════════════════════════════╗")
    logger.info(f"║  TweetSupport AI Support Agent Pipeline      ║")
    logger.info(f"║  Brand: {active_brand:<37s} ║")
    logger.info(f"║  Subsample: {active_subsample_size:<33d} ║")
    logger.info(f"╚══════════════════════════════════════════════╝")

    if args.smoke_test:
        logger.info("SMOKE TEST MODE: Using small subsample (100).")
    
        logger.info("🧪 SMOKE TEST MODE: Using small subsample (100).")

    # Ensure directories exist
    ensure_directories()
    

    # Pipeline execution
    total_start = time.time()
    

    # Step 1: Download
    if not args.skip_download:
        run_step("Data Download", download_data)
        run_step("Data Download", step_download)
    else:
        logger.info("Skipping data download as requested.\n")
        
    run_step("Preprocessing", preprocess_data, active_brand, active_subsample_size)
    run_step("Intent Discovery", discover_intents)
    run_step("Retriever Indexing", build_retriever_index)
    run_step("Evaluation", run_evaluation)
    

    # Step 2: Preprocess
    threads_path = run_step("Preprocessing", step_preprocess, active_brand, active_subsample_size)

    # Step 3: Intent Discovery
    if not args.skip_intents:
        taxonomy = run_step("Intent Discovery", step_discover_intents, threads_path)
    else:
        from intent.discover import load_taxonomy
        taxonomy = load_taxonomy()
        logger.info("Using existing intent taxonomy.\n")

    # Step 4: Build Golden Set
    golden_set_path = run_step("Golden Set Construction", step_build_golden_set, threads_path, taxonomy)

    # Step 5: Evaluation
    if not args.skip_eval:
        run_step("Evaluation", step_evaluate, golden_set_path, threads_path)

    total_elapsed = time.time() - total_start
    logger.info(f"=== Entire Pipeline Completed in {total_elapsed:.2f} seconds ===")
    logger.info(f"═══════════════════════════════════════════════")
    logger.info(f"  Pipeline Completed in {total_elapsed:.2f} seconds")
    logger.info(f"  Results saved to: {RESULTS_DIR}")
    logger.info(f"═══════════════════════════════════════════════")


if __name__ == "__main__":
    main()
