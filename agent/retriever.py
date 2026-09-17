import logging
import json
import os
import faiss
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple

from config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class ThreadRetriever:
    """
    Retrieves similar historical threads using FAISS and sentence transformers.
    """

    def __init__(self, threads: List[Dict[str, Any]], model_name: str = None):
        """
        Initializes the ThreadRetriever.
        
        Args:
            threads: A list of dictionaries representing the historical threads.
            model_name: The name of the sentence-transformers model to use.
        """
        self.threads = [t for t in threads if t.get("first_customer_message") and len(t["first_customer_message"].strip()) > 5]
        self.model_name = model_name or EMBEDDING_MODEL
        logger.info(f"Loading embedding model '{self.model_name}'...")
        self.model = SentenceTransformer(self.model_name)
        self.index = None
        self._build_index()

    def _build_index(self):
        """Builds the FAISS index from the loaded threads."""
        if not self.threads:
            logger.warning("No valid threads provided to build the index.")
            return

        logger.info(f"Building FAISS index for {len(self.threads)} threads...")
        messages = [t["first_customer_message"] for t in self.threads]
        
        # Encode messages with progress bar
        embeddings = self.model.encode(messages, show_progress_bar=True, convert_to_numpy=True)
        
        # Normalize for cosine similarity (Inner Product on normalized vectors)
        faiss.normalize_L2(embeddings)
        
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        logger.info("FAISS index built successfully.")

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most similar threads for a given query.
        
        Args:
            query: The customer message to search for.
            top_k: Number of similar threads to return.
            
        Returns:
            A list of the top-k similar threads, augmented with 'similarity_score'.
        """
        if not self.index:
            logger.warning("Index not built. Cannot retrieve.")
            return []
            
        if not query or len(query.strip()) < 3:
            logger.warning("Query is too short for meaningful retrieval.")
            return []

        # Encode and normalize query
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        distances, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.threads):
                thread = dict(self.threads[idx])
                thread["similarity_score"] = float(distances[0][i])
                results.append(thread)
                
        return results

    def save_index(self, path: str):
        """Saves the FAISS index to disk."""
        if self.index:
            faiss.write_index(self.index, path)
            logger.info(f"Index saved to {path}")
        else:
            logger.error("No index to save.")

    @classmethod
    def load_index(cls, path: str, threads: List[Dict[str, Any]], model_name: str = None) -> 'ThreadRetriever':
        """Loads a FAISS index from disk and initializes a ThreadRetriever."""
        retriever = cls.__new__(cls)
        retriever.threads = [t for t in threads if t.get("first_customer_message") and len(t["first_customer_message"].strip()) > 5]
        retriever.model_name = model_name or EMBEDDING_MODEL
        logger.info(f"Loading embedding model '{retriever.model_name}'...")
        retriever.model = SentenceTransformer(retriever.model_name)
        
        if os.path.exists(path):
            retriever.index = faiss.read_index(path)
            logger.info(f"Loaded FAISS index from {path}")
        else:
            logger.warning(f"Index path {path} not found. Building new index...")
            retriever._build_index()
            
        return retriever
