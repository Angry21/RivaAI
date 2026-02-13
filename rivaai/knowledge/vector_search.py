"""Vector similarity search engine using PostgreSQL with pgvector."""

import asyncio
import logging
from typing import List, Optional

from rivaai.config.database import DatabasePool
from rivaai.config.settings import Settings
from rivaai.knowledge.models import DatabaseError, RawSearchResult, ValidationError

logger = logging.getLogger(__name__)


class VectorSearchEngine:
    """PostgreSQL + pgvector search engine for semantic similarity search."""

    def __init__(self, db_pool: DatabasePool, settings: Settings) -> None:
        """Initialize vector search engine.

        Args:
            db_pool: Database connection pool
            settings: Application settings
        """
        self.db_pool = db_pool
        self.settings = settings
        logger.info("VectorSearchEngine initialized")

    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int,
        domain: Optional[str] = None,
        threshold: float = 0.0,
    ) -> List[RawSearchResult]:
        """Perform cosine similarity search using pgvector.

        Args:
            query_embedding: 1536-dim query vector
            top_k: Number of results to retrieve (1-20)
            domain: Optional domain filter ('agriculture', 'welfare', 'education')
            threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of raw search results with similarity scores

        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If search query fails
        """
        # Validate input parameters
        self._validate_parameters(top_k, threshold)

        # Build query with optional domain filter
        query = self._build_query(domain)

        # Execute search with retry logic
        results = await self._execute_search_with_retry(
            query, query_embedding, top_k, threshold, domain
        )

        logger.info(
            f"Vector search completed: {len(results)} results (top_k={top_k}, "
            f"threshold={threshold}, domain={domain})"
        )

        return results

    def _validate_parameters(self, top_k: int, threshold: float) -> None:
        """Validate input parameters.

        Args:
            top_k: Number of results to retrieve
            threshold: Minimum similarity score

        Raises:
            ValidationError: If parameters are invalid
        """
        if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
            raise ValidationError(f"top_k must be between 1 and 20, got {top_k}")

        if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
            raise ValidationError(f"threshold must be between 0.0 and 1.0, got {threshold}")

    def _build_query(self, domain: Optional[str]) -> str:
        """Build SQL query with optional domain filter.

        Args:
            domain: Optional domain filter

        Returns:
            SQL query string
        """
        base_query = """
            SELECT 
                item_id::text as doc_id,
                content,
                metadata,
                (1 - (embedding <=> %s::vector)) as similarity,
                domain,
                entity_type,
                source_table
            FROM knowledge_items
        """

        if domain:
            base_query += " WHERE domain = %s"

        base_query += """
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        return base_query

    async def _execute_search_with_retry(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int,
        threshold: float,
        domain: Optional[str],
    ) -> List[RawSearchResult]:
        """Execute search with exponential backoff retry logic.

        Args:
            query: SQL query string
            query_embedding: Query embedding vector
            top_k: Number of results
            threshold: Minimum similarity score
            domain: Optional domain filter

        Returns:
            List of raw search results

        Raises:
            DatabaseError: If all retry attempts fail
        """
        max_retries = 3
        backoff_delays = [0.1, 0.2, 0.4]  # 100ms, 200ms, 400ms

        for attempt in range(max_retries):
            try:
                return await self._execute_search(
                    query, query_embedding, top_k, threshold, domain
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = backoff_delays[attempt]
                    logger.warning(
                        f"Database query failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Database query failed after {max_retries} attempts: {e}"
                    )
                    raise DatabaseError(
                        f"Vector search failed after {max_retries} retries: {e}"
                    ) from e

        # This should never be reached, but satisfies type checker
        raise DatabaseError("Vector search failed unexpectedly")

    async def _execute_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int,
        threshold: float,
        domain: Optional[str],
    ) -> List[RawSearchResult]:
        """Execute the actual database search.

        Args:
            query: SQL query string
            query_embedding: Query embedding vector
            top_k: Number of results
            threshold: Minimum similarity score
            domain: Optional domain filter

        Returns:
            List of raw search results
        """
        # Convert embedding to string format for pgvector
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Build parameters based on whether domain filter is used
        if domain:
            params = (embedding_str, domain, embedding_str, top_k)
        else:
            params = (embedding_str, embedding_str, top_k)

        # Execute query synchronously (psycopg2 is not async)
        # We'll use asyncio.to_thread to avoid blocking
        results = await asyncio.to_thread(
            self._execute_query_sync, query, params, threshold
        )

        return results

    def _execute_query_sync(
        self, query: str, params: tuple, threshold: float
    ) -> List[RawSearchResult]:
        """Execute query synchronously and parse results.

        Args:
            query: SQL query string
            params: Query parameters
            threshold: Minimum similarity score

        Returns:
            List of raw search results
        """
        conn = self.db_pool.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    doc_id, content, metadata, similarity, domain, entity_type, source_table = row

                    # Apply threshold filtering
                    if similarity >= threshold:
                        results.append(
                            RawSearchResult(
                                doc_id=doc_id,
                                content=content,
                                metadata=metadata,
                                similarity=similarity,
                                domain=domain,
                                entity_type=entity_type,
                                source_table=source_table,
                            )
                        )

                # Sort by similarity descending and doc_id for tie-breaking
                results.sort(key=lambda x: (-x.similarity, x.doc_id))

                return results
        finally:
            self.db_pool.release_connection(conn)
