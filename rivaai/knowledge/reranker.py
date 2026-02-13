"""Hybrid reranker for search result reordering using vector + keyword scoring."""

import logging
from typing import List

from rivaai.config.settings import Settings
from rivaai.knowledge.models import RawSearchResult, SearchResult

logger = logging.getLogger(__name__)


class HybridReranker:
    """Hybrid reranker using vector + keyword scoring.
    
    Combines vector similarity scores with keyword matching scores to improve
    result relevance. Uses Jaccard similarity for keyword scoring.
    """

    def __init__(
        self,
        settings: Settings,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        """Initialize reranker with scoring weights.
        
        Args:
            settings: Application settings
            vector_weight: Weight for vector similarity score (default: 0.7)
            keyword_weight: Weight for keyword match score (default: 0.3)
        """
        self.settings = settings
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        logger.info(
            f"HybridReranker initialized with weights: "
            f"vector={vector_weight}, keyword={keyword_weight}"
        )

    async def rerank(
        self,
        query: str,
        results: List[RawSearchResult],
    ) -> List[SearchResult]:
        """Rerank results using hybrid scoring.
        
        Combines vector similarity with keyword matching using Jaccard similarity.
        Falls back to vector-only ordering if keyword scoring fails.
        
        Args:
            query: Original query text
            results: Initial search results from vector search
            
        Returns:
            Reranked search results sorted by hybrid score
        """
        if not results:
            return []
        
        try:
            # Calculate hybrid scores for all results
            scored_results = []
            for result in results:
                keyword_score = self._keyword_score(query, result.content)
                reranked_score = (
                    self.vector_weight * result.similarity
                    + self.keyword_weight * keyword_score
                )
                
                # Convert RawSearchResult to SearchResult with reranked score
                search_result = SearchResult(
                    doc_id=result.doc_id,
                    content=result.content,
                    metadata=result.metadata,
                    similarity_score=result.similarity,
                    reranked_score=reranked_score,
                    domain=result.domain,
                    entity_type=result.entity_type,
                    source_table=result.source_table,
                )
                scored_results.append(search_result)
            
            # Sort by reranked score descending
            scored_results.sort(key=lambda x: -x.reranked_score)
            
            logger.info(
                f"Reranked {len(scored_results)} results "
                f"(score range: {scored_results[-1].reranked_score:.4f} - "
                f"{scored_results[0].reranked_score:.4f})"
            )
            
            return scored_results
            
        except Exception as e:
            # Fallback to vector-only ordering
            logger.error(
                f"Reranking failed for query '{query[:50]}...': {e}. "
                f"Falling back to vector-only ordering."
            )
            
            # Convert to SearchResult with original similarity as reranked score
            fallback_results = [
                SearchResult(
                    doc_id=result.doc_id,
                    content=result.content,
                    metadata=result.metadata,
                    similarity_score=result.similarity,
                    reranked_score=result.similarity,
                    domain=result.domain,
                    entity_type=result.entity_type,
                    source_table=result.source_table,
                )
                for result in results
            ]
            
            # Sort by similarity descending
            fallback_results.sort(key=lambda x: -x.similarity_score)
            
            return fallback_results

    def _keyword_score(self, query: str, document: str) -> float:
        """Calculate keyword match score using Jaccard similarity.
        
        Uses Jaccard similarity: score = |query ∩ doc| / |query ∪ doc|
        This is more robust than simple term overlap ratio and handles
        length mismatches and common stopwords better.
        
        Args:
            query: Query text
            document: Document text
            
        Returns:
            Keyword match score between 0.0 and 1.0
        """
        # Tokenize and normalize to lowercase
        query_terms = set(query.lower().split())
        doc_terms = set(document.lower().split())
        
        # Handle empty sets
        if not query_terms or not doc_terms:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(query_terms & doc_terms)
        union = len(query_terms | doc_terms)
        
        if union == 0:
            return 0.0
        
        return intersection / union
