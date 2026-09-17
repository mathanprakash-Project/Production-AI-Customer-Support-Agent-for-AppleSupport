"""
Central configuration module for the TweetSupport AI Support Agent project.
Loads environment variables from .env and sets up default paths and constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Models
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Brand specific settings
BRAND = os.getenv("BRAND", "AppleSupport")

# Directories
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"

# Execution parameters
SUBSAMPLE_SIZE = int(os.getenv("SUBSAMPLE_SIZE", 5000))
GOLDEN_SET_SIZE = int(os.getenv("GOLDEN_SET_SIZE", 200))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 3))

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [DATA_DIR, PROCESSED_DIR, RESULTS_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Create required directories on import
ensure_directories()
