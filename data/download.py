import os
import logging
from pathlib import Path
from typing import Optional
import kagglehub
from datasets import load_dataset

logger = logging.getLogger(__name__)

def download_dataset(data_dir: str) -> Optional[str]:
    """
    Downloads the 'thoughtvector/customer-support-on-twitter' dataset using kagglehub.
    
    Args:
        data_dir: Directory to save/link the data
        
    Returns:
        Path to the downloaded twcs.csv file, or None if failed.
    """
    try:
        logger.info("Downloading/verifying Kaggle dataset 'thoughtvector/customer-support-on-twitter'...")
        path = kagglehub.dataset_download("thoughtvector/customer-support-on-twitter")
        
        csv_path = Path(path) / "twcs.csv"
        if csv_path.exists():
            logger.info(f"Dataset downloaded/found successfully at {csv_path}")
            return str(csv_path)
        else:
            logger.error(f"Expected twcs.csv not found in downloaded path: {path}")
            return None
    except Exception as e:
        logger.error(f"Failed to download dataset: {e}")
        return None

def download_banking77(data_dir: str) -> bool:
    """
    Downloads the BANKING77 dataset using HuggingFace datasets library.
    
    Args:
        data_dir: Directory to save the dataset cache
        
    Returns:
        bool indicating success.
    """
    try:
        logger.info("Downloading BANKING77 dataset...")
        dataset = load_dataset("PolyAI/banking77", cache_dir=data_dir)
        logger.info("BANKING77 dataset downloaded successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to download BANKING77 dataset: {e}")
        return False
