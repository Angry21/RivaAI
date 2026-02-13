"""Unit tests for VectorSearchEngine.

Tests error handling, edge cases, and specific scenarios.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from rivaai.config.database import DatabasePool
from rivaai.config.settings import Settings
from rivaai.knowledge.models import DatabaseError, RawSearchResult, ValidationError
from rivaai.knowledge.vector_search import VectorSearchEngine


@pytest.fixture
def mock_db_pool():
    """Create mock database pool."""
    return Mock(spec=DatabasePool)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return Mock(spec=Settings)


@pytest.fixture
def search_engine(mock_db_pool, mock_settings):
    """Create VectorSearchEngine instance."""
    return VectorSearchEngine(mock_db_pool, mock_settings)


@pytest.fixture
def sample_embedding():
    """Create sample 1536-dim embedding."""
    return [0.1] * 1536


class TestEmptyResults:
    """Test empty result set handling."""

    @pytest.mark.asyncio
    async def test_empty_database_returns_empty_list(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that empty database returns empty list without error."""
        # Mock empty database result
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.0
        )

        # Verify empty list returned
        assert results == []
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_threshold_filters_all_results(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that high threshold filters all results."""
        # Mock database with low similarity scores
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("doc_1", "Content 1", {}, 0.3, "agriculture", "crop", "knowledge_items"),
            ("doc_2", "Content 2", {}, 0.2, "agriculture", "crop", "knowledge_items"),
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search with high threshold
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.8
        )

        # Verify all results filtered
        assert results == []


class TestDatabaseErrors:
    """Test database connection and query error handling."""

    @pytest.mark.asyncio
    async def test_database_connection_failure_with_retry(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test retry logic on database connection failure."""
        # Mock connection failure
        mock_db_pool.get_connection.side_effect = Exception("Connection failed")

        # Execute search and expect DatabaseError after retries
        with pytest.raises(DatabaseError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=5, threshold=0.0
            )

        # Verify error message mentions retries
        assert "retries" in str(exc_info.value).lower()
        assert "3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_query_failure_retries_then_fails(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that query failures trigger retries before raising error."""
        # Mock query execution failure
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Query execution failed")
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search and expect DatabaseError
        with pytest.raises(DatabaseError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=5, threshold=0.0
            )

        # Verify retries occurred (3 connection attempts)
        assert mock_db_pool.get_connection.call_count == 3

    @pytest.mark.asyncio
    async def test_database_recovers_on_second_attempt(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test successful recovery on retry."""
        # Mock first attempt fails, second succeeds
        mock_conn_fail = Mock()
        mock_cursor_fail = Mock()
        mock_cursor_fail.execute.side_effect = Exception("Temporary failure")
        mock_cursor_fail.__enter__ = Mock(return_value=mock_cursor_fail)
        mock_cursor_fail.__exit__ = Mock(return_value=False)
        mock_conn_fail.cursor.return_value = mock_cursor_fail

        mock_conn_success = Mock()
        mock_cursor_success = Mock()
        mock_cursor_success.fetchall.return_value = [
            ("doc_1", "Content", {}, 0.9, "agriculture", "crop", "knowledge_items")
        ]
        mock_cursor_success.__enter__ = Mock(return_value=mock_cursor_success)
        mock_cursor_success.__exit__ = Mock(return_value=False)
        mock_conn_success.cursor.return_value = mock_cursor_success

        mock_db_pool.get_connection.side_effect = [mock_conn_fail, mock_conn_success]
        mock_db_pool.release_connection = Mock()

        # Execute search - should succeed on second attempt
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.0
        )

        # Verify results returned
        assert len(results) == 1
        assert results[0].doc_id == "doc_1"


class TestInputValidation:
    """Test input parameter validation."""

    @pytest.mark.asyncio
    async def test_top_k_zero_raises_validation_error(
        self, search_engine, sample_embedding
    ):
        """Test that top_k=0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=0, threshold=0.5
            )

        assert "top_k" in str(exc_info.value).lower()
        assert "0" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_top_k_negative_raises_validation_error(
        self, search_engine, sample_embedding
    ):
        """Test that negative top_k raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=-5, threshold=0.5
            )

        assert "top_k" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_top_k_too_large_raises_validation_error(
        self, search_engine, sample_embedding
    ):
        """Test that top_k > 20 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=25, threshold=0.5
            )

        assert "top_k" in str(exc_info.value).lower()
        assert "25" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_threshold_negative_raises_validation_error(
        self, search_engine, sample_embedding
    ):
        """Test that negative threshold raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=5, threshold=-0.1
            )

        assert "threshold" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_threshold_too_large_raises_validation_error(
        self, search_engine, sample_embedding
    ):
        """Test that threshold > 1.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await search_engine.similarity_search(
                sample_embedding, top_k=5, threshold=1.5
            )

        assert "threshold" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_valid_boundary_values_accepted(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that boundary values (1, 20, 0.0, 1.0) are accepted."""
        # Mock successful database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Test boundary values
        await search_engine.similarity_search(sample_embedding, top_k=1, threshold=0.0)
        await search_engine.similarity_search(sample_embedding, top_k=20, threshold=1.0)
        await search_engine.similarity_search(sample_embedding, top_k=10, threshold=0.5)


class TestThresholdFiltering:
    """Test threshold filtering edge cases."""

    @pytest.mark.asyncio
    async def test_exact_threshold_match_included(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that results exactly matching threshold are included."""
        # Mock result with exact threshold match
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("doc_1", "Content", {}, 0.7, "agriculture", "crop", "knowledge_items")
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Search with threshold = 0.7
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.7
        )

        # Verify result included (>= threshold)
        assert len(results) == 1
        assert results[0].similarity == 0.7

    @pytest.mark.asyncio
    async def test_below_threshold_excluded(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that results below threshold are excluded."""
        # Mock results with varying similarities
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("doc_1", "Content 1", {}, 0.8, "agriculture", "crop", "knowledge_items"),
            ("doc_2", "Content 2", {}, 0.6, "agriculture", "crop", "knowledge_items"),
            ("doc_3", "Content 3", {}, 0.4, "agriculture", "crop", "knowledge_items"),
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Search with threshold = 0.7
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.7
        )

        # Verify only doc_1 included
        assert len(results) == 1
        assert results[0].doc_id == "doc_1"
        assert results[0].similarity >= 0.7


class TestDomainFiltering:
    """Test domain filtering functionality."""

    @pytest.mark.asyncio
    async def test_domain_filter_applied_in_query(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that domain filter is applied in SQL query."""
        # Mock database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("doc_1", "Content", {}, 0.9, "agriculture", "crop", "knowledge_items")
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search with domain filter
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, domain="agriculture", threshold=0.0
        )

        # Verify query was called with domain parameter
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "WHERE domain = %s" in query
        assert "agriculture" in params

    @pytest.mark.asyncio
    async def test_no_domain_filter_searches_all(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that no domain filter searches all domains."""
        # Mock database response
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search without domain filter
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.0
        )

        # Verify query does not have WHERE clause for domain
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]

        assert "WHERE domain" not in query


class TestResultOrdering:
    """Test result ordering and tie-breaking."""

    @pytest.mark.asyncio
    async def test_results_ordered_by_similarity_descending(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that results are ordered by similarity (highest first)."""
        # Mock results in random order
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("doc_1", "Content 1", {}, 0.5, "agriculture", "crop", "knowledge_items"),
            ("doc_2", "Content 2", {}, 0.9, "agriculture", "crop", "knowledge_items"),
            ("doc_3", "Content 3", {}, 0.7, "agriculture", "crop", "knowledge_items"),
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.0
        )

        # Verify ordering
        assert len(results) == 3
        assert results[0].similarity == 0.9
        assert results[1].similarity == 0.7
        assert results[2].similarity == 0.5

    @pytest.mark.asyncio
    async def test_tie_breaking_by_doc_id(
        self, search_engine, mock_db_pool, sample_embedding
    ):
        """Test that ties are broken by doc_id alphabetically."""
        # Mock results with identical similarities
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("doc_C", "Content C", {}, 0.8, "agriculture", "crop", "knowledge_items"),
            ("doc_A", "Content A", {}, 0.8, "agriculture", "crop", "knowledge_items"),
            ("doc_B", "Content B", {}, 0.8, "agriculture", "crop", "knowledge_items"),
        ]
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor
        mock_db_pool.get_connection.return_value = mock_conn
        mock_db_pool.release_connection = Mock()

        # Execute search
        results = await search_engine.similarity_search(
            sample_embedding, top_k=5, threshold=0.0
        )

        # Verify tie-breaking by doc_id
        assert len(results) == 3
        assert results[0].doc_id == "doc_A"
        assert results[1].doc_id == "doc_B"
        assert results[2].doc_id == "doc_C"
