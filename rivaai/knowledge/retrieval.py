"""Main retrieval system interface for knowledge base search."""

import asyncio
import logging
import time
from typing import List, Optional

from rivaai.config.database import DatabasePool
from rivaai.config.settings import Settings
from rivaai.knowledge.embeddings import EmbeddingGenerator
from rivaai.knowledge.models import (
    DatabaseError,
    EmbeddingError,
    SearchResult,
    ValidationError,
)
from rivaai.knowledge.rag_formatter import RAGFormatter
from rivaai.knowledge.reranker import HybridReranker
from rivaai.knowledge.vector_search import VectorSearchEngine

logger = logging.getLogger(__name__)


class RetrievalSystem:
    """Main retrieval system interface for semantic search.
    
    Integrates vector search, hybrid reranking, and RAG formatting to provide
    end-to-end retrieval capabilities for the knowledge base.
    """

    def __init__(
        self,
        db_pool: DatabasePool,
        embedding_gen: EmbeddingGenerator,
        settings: Settings,
    ) -> None:
        """Initialize retrieval system with dependencies.
        
        Args:
            db_pool: Database connection pool
            embedding_gen: Embedding generator for query encoding
            settings: Application settings
        """
        self.db_pool = db_pool
        self.embedding_gen = embedding_gen
        self.settings = settings
        
        # Initialize components
        self.vector_search = VectorSearchEngine(db_pool, settings)
        self.reranker = HybridReranker(settings)
        self.formatter = RAGFormatter()
        
        # Latency thresholds
        self.vector_search_threshold_ms = 300
        self.end_to_end_threshold_ms = 500
        
        logger.info("RetrievalSystem initialized with all components")

    async def search(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """Perform semantic search across knowledge base.
        
        End-to-end retrieval flow:
        1. Generate query embedding
        2. Perform vector similarity search
        3. Apply hybrid reranking
        4. Filter by relevance threshold
        5. Log metrics and warnings
        
        Args:
            query: Natural language query in any supported language
            domain: Optional domain filter ('agriculture', 'welfare', 'education')
            top_k: Number of results to return (1-20)
            threshold: Minimum similarity score (0.0-1.0), defaults to config
            
        Returns:
            List of SearchResult objects sorted by relevance
            
        Raises:
            ValueError: If top_k out of range or threshold invalid
            EmbeddingError: If embedding generation fails
            DatabaseError: If vector search fails
        """
        start_time = time.time()
        
        # Validate inputs
        self._validate_search_params(query, top_k, threshold)
        
        # Use configured threshold if not provided
        if threshold is None:
            threshold = self.settings.retrieval_relevance_threshold
        
        try:
            # Step 1: Generate query embedding
            embedding_start = time.time()
            try:
                query_embedding = await asyncio.to_thread(
                    self.embedding_gen.generate_embedding, query
                )
            except Exception as e:
                logger.error(f"Embedding generation failed for query '{query[:50]}...': {e}")
                raise EmbeddingError(f"Failed to generate query embedding: {e}") from e
            embedding_time = (time.time() - embedding_start) * 1000
            
            # Step 2: Perform vector similarity search
            search_start = time.time()
            raw_results = await self.vector_search.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k,
                domain=domain,
                threshold=0.0,  # Apply threshold after reranking
            )
            search_time = (time.time() - search_start) * 1000
            
            # Log warning if vector search is slow
            if search_time > self.vector_search_threshold_ms:
                logger.warning(
                    f"Vector search exceeded threshold: {search_time:.0f}ms > "
                    f"{self.vector_search_threshold_ms}ms (query: '{query[:50]}...')"
                )
            
            # Step 3: Apply hybrid reranking
            rerank_start = time.time()
            reranked_results = await self.reranker.rerank(query, raw_results)
            rerank_time = (time.time() - rerank_start) * 1000
            
            # Step 4: Filter by relevance threshold
            filtered_results = [
                result for result in reranked_results
                if result.similarity_score >= threshold
            ]
            
            # Log number of filtered documents
            filtered_count = len(reranked_results) - len(filtered_results)
            if filtered_count > 0:
                logger.info(
                    f"Filtered {filtered_count} documents below threshold {threshold}"
                )
            
            # Calculate total time
            total_time = (time.time() - start_time) * 1000
            
            # Log warning if end-to-end retrieval is slow
            if total_time > self.end_to_end_threshold_ms:
                logger.warning(
                    f"End-to-end retrieval exceeded threshold: {total_time:.0f}ms > "
                    f"{self.end_to_end_threshold_ms}ms"
                )
            
            # Step 5: Log metrics
            self._log_retrieval_metrics(
                query=query,
                result_count=len(filtered_results),
                embedding_time=embedding_time,
                search_time=search_time,
                rerank_time=rerank_time,
                total_time=total_time,
                results=filtered_results,
            )
            
            return filtered_results
            
        except (EmbeddingError, DatabaseError, ValidationError):
            # Re-raise known errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during retrieval: {e}")
            raise DatabaseError(f"Retrieval failed: {e}") from e

    async def search_batch(
        self,
        queries: List[str],
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> List[List[SearchResult]]:
        """Perform batch retrieval for multiple queries.
        
        Processes multiple queries efficiently by:
        1. Generating embeddings in a single batch request
        2. Executing similarity searches for all queries
        3. Applying reranking to each result set
        4. Maintaining query order correspondence
        
        Args:
            queries: List of natural language queries
            domain: Optional domain filter
            top_k: Number of results per query
            
        Returns:
            List of result lists, one per query (maintains order)
        """
        if not queries:
            return []
        
        start_time = time.time()
        
        try:
            # Step 1: Generate embeddings in batch
            embedding_start = time.time()
            try:
                query_embeddings = await asyncio.to_thread(
                    self.embedding_gen.generate_embeddings_batch, queries
                )
            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}")
                raise EmbeddingError(f"Failed to generate batch embeddings: {e}") from e
            embedding_time = (time.time() - embedding_start) * 1000
            
            # Step 2: Execute similarity searches for all queries
            search_start = time.time()
            threshold = self.settings.retrieval_relevance_threshold
            
            # Process searches concurrently
            search_tasks = [
                self.vector_search.similarity_search(
                    query_embedding=embedding,
                    top_k=top_k,
                    domain=domain,
                    threshold=0.0,  # Apply threshold after reranking
                )
                for embedding in query_embeddings
            ]
            
            raw_results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
            search_time = (time.time() - search_start) * 1000
            
            # Step 3: Apply reranking to each result set
            rerank_start = time.time()
            final_results = []
            
            for idx, (query, raw_results) in enumerate(zip(queries, raw_results_list)):
                # Handle individual query failures
                if isinstance(raw_results, Exception):
                    logger.error(
                        f"Search failed for query {idx} ('{query[:50]}...'): {raw_results}"
                    )
                    final_results.append([])  # Empty list for failed query
                    continue
                
                # Rerank results
                try:
                    reranked = await self.reranker.rerank(query, raw_results)
                    
                    # Filter by relevance threshold
                    filtered = [
                        result for result in reranked
                        if result.similarity_score >= threshold
                    ]
                    
                    final_results.append(filtered)
                except Exception as e:
                    logger.error(
                        f"Reranking failed for query {idx} ('{query[:50]}...'): {e}"
                    )
                    final_results.append([])  # Empty list for failed reranking
            
            rerank_time = (time.time() - rerank_start) * 1000
            
            # Calculate total time
            total_time = (time.time() - start_time) * 1000
            
            # Log batch metrics
            total_results = sum(len(results) for results in final_results)
            logger.info(
                f"Batch retrieval completed: queries={len(queries)}, "
                f"total_results={total_results}, "
                f"latency={{embedding={embedding_time:.0f}ms, "
                f"search={search_time:.0f}ms, "
                f"rerank={rerank_time:.0f}ms, "
                f"total={total_time:.0f}ms}}"
            )
            
            return final_results
            
        except (EmbeddingError, DatabaseError):
            # Re-raise known errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during batch retrieval: {e}")
            raise DatabaseError(f"Batch retrieval failed: {e}") from e

    async def format_for_rag(
        self,
        results: List[SearchResult],
        max_tokens: int = 2000,
    ) -> str:
        """Format search results as LLM context string.
        
        Args:
            results: Search results to format
            max_tokens: Maximum token budget for context
            
        Returns:
            Formatted context string with document delimiters
        """
        return self.formatter.format_context(results, max_tokens=max_tokens)

    def _validate_search_params(
        self,
        query: str,
        top_k: int,
        threshold: Optional[float],
    ) -> None:
        """Validate search parameters.
        
        Args:
            query: Query string
            top_k: Number of results
            threshold: Relevance threshold
            
        Raises:
            ValidationError: If parameters are invalid
        """
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            raise ValidationError(f"top_k must be between 1 and 20, got {top_k}")
        
        if threshold is not None:
            if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
                raise ValidationError(
                    f"threshold must be between 0.0 and 1.0, got {threshold}"
                )

    def _log_retrieval_metrics(
        self,
        query: str,
        result_count: int,
        embedding_time: float,
        search_time: float,
        rerank_time: float,
        total_time: float,
        results: List[SearchResult],
    ) -> None:
        """Log detailed retrieval metrics.
        
        Args:
            query: Query text
            result_count: Number of results returned
            embedding_time: Embedding generation time (ms)
            search_time: Vector search time (ms)
            rerank_time: Reranking time (ms)
            total_time: Total end-to-end time (ms)
            results: Search results
        """
        # Truncate query for logging
        query_preview = query[:100] + "..." if len(query) > 100 else query
        
        # Calculate similarity score distribution
        if results:
            scores = [r.similarity_score for r in results]
            score_min = min(scores)
            score_max = max(scores)
            score_mean = sum(scores) / len(scores)
        else:
            score_min = score_max = score_mean = 0.0
        
        logger.info(
            f"Retrieval completed: query='{query_preview}', "
            f"results={result_count}, "
            f"latency={{embedding={embedding_time:.0f}ms, "
            f"search={search_time:.0f}ms, "
            f"rerank={rerank_time:.0f}ms, "
            f"total={total_time:.0f}ms}}, "
            f"scores={{min={score_min:.4f}, max={score_max:.4f}, mean={score_mean:.4f}}}"
        )

