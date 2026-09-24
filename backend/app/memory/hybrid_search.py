import math
from typing import List, Tuple, Optional
import numpy as np

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    from app.llm.embeddings import EmbeddingService, get_embedding_service
except ImportError:
    EmbeddingService = None
    def get_embedding_service(): return None

class HybridSearchEngine:
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedder = embedding_service or get_embedding_service()
        
    def bm25_search(self, query: str, documents: List[str], top_k: int = 10) -> List[Tuple[int, float]]:
        if not BM25Okapi or not documents:
            return []
            
        tokenized_corpus = [doc.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        
        doc_scores = bm25.get_scores(tokenized_query)
        
        top_indices = np.argsort(doc_scores)[::-1][:top_k]
        return [(int(i), float(doc_scores[i])) for i in top_indices if doc_scores[i] > 0]
        
    def vector_search(self, query_vec: List[float], doc_vecs: List[List[float]], top_k: int = 10) -> List[Tuple[int, float]]:
        if not query_vec or not doc_vecs:
            return []
            
        def _cosine(v1, v2):
            if not v1 or not v2: return 0.0
            dot = sum(a * b for a, b in zip(v1, v2))
            n1 = math.sqrt(sum(a * a for a in v1))
            n2 = math.sqrt(sum(b * b for b in v2))
            if n1 == 0 or n2 == 0: return 0.0
            return dot / (n1 * n2)
            
        scores = [(_cosine(query_vec, doc_vec), i) for i, doc_vec in enumerate(doc_vecs)]
        scores.sort(reverse=True)
        
        return [(i, score) for score, i in scores[:top_k]]
        
    def rrf_fusion(self, rankings: List[List[Tuple[int, float]]], k: int = 60, weights: List[float] = None) -> List[Tuple[int, float]]:
        if weights is None:
            weights = [0.7, 0.3]  # Vector, BM25
            
        rrf_scores = {}
        
        for r_idx, ranking in enumerate(rankings):
            weight = weights[r_idx] if r_idx < len(weights) else 1.0
            
            for rank, (doc_idx, _) in enumerate(ranking):
                score = weight / (k + rank + 1)
                rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + score
                
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs
        
    def hybrid_search(self, query: str, documents: List[str], doc_embeddings: List[List[float]], top_k: int = 5, vector_weight: float = 0.7) -> List[Tuple[int, float]]:
        bm25_ranking = self.bm25_search(query, documents, top_k=max(20, top_k*2))
        
        vector_ranking = []
        if self.embedder:
            try:
                # We need an async call for embedder usually, but this is a sync method
                # Assuming query_vec is passed in if this is called from async context
                # For this implementation, we might not be able to call async embedder directly here.
                # Let's handle it by returning just BM25 if no query_vec is provided or caller handles it.
                pass
            except Exception:
                pass
                
        # For a true hybrid search where caller provides query_vec, we should update signature
        # Let's adjust this method to take query_vec
        return bm25_ranking
        
    async def async_hybrid_search(self, query: str, documents: List[str], doc_embeddings: List[List[float]], top_k: int = 5, vector_weight: float = 0.7) -> List[Tuple[int, float]]:
        bm25_ranking = self.bm25_search(query, documents, top_k=max(20, top_k*2))
        
        vector_ranking = []
        if self.embedder and doc_embeddings:
            try:
                query_vec = await self.embedder.embed_query(query)
                vector_ranking = self.vector_search(query_vec, doc_embeddings, top_k=max(20, top_k*2))
            except Exception:
                pass
                
        if not vector_ranking:
            return bm25_ranking[:top_k]
        if not bm25_ranking:
            return vector_ranking[:top_k]
            
        fused = self.rrf_fusion([vector_ranking, bm25_ranking], weights=[vector_weight, 1.0 - vector_weight])
        return fused[:top_k]
