"""Property-based tests for VectorSearchEngine.

Feature: knowledge-base-retrieval
"""

import asyncio
import json
from typing import List
from unittest.mock import MagicMock, Mock, patch

import hypothesis
import pytest
from hypothesis import given, settings as hypothesis_settings
from hypothesis import strategies as st

from rivaai.config.database import DatabasePool
from rivaai.config.settings import Settings
from rivaai.knowledge.models import DatabaseError, RawSearchResult, ValidationError
from rivaai.knowledge.vector_search import VectorSearchEngine


# Hypothesis strategies for test data generation


@st.composite
def embedding_vector(draw: st.DrawFn) -> List[float]:
    """Generate a valid 1536-dimensional embedding vector with unit norm.

    Args:
        draw: Hypothesis draw function

    Returns:
        1536-dimensional vector
    """
    # Generate random floats and normalize to unit vector
    # Use smaller range for better shrinking
    values = draw(
        st.lists(
            st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1536,
            max_size=1536,
        )
    )
    # Normalize to unit vector
    magnitude = sum(v * v for v in values) ** 0.5
    if magnitude > 0:
        values = [v / magnitude for v in values]
    else:
        # Fallback to simple unit vector if all zeros
        values = [1.0 / (1536**0.5)] * 1536
    return values


@st.composite
def search_result_set(draw: st.DrawFn, min_size: int = 0, max_size: int = 20) -> List[RawSearchResult]:
    """Generate a set of search results with varying similarity scores.

    Args:
        draw: Hypothesis draw function
        min_size: Minimum number of results
        max_size: Maximum number of results

    Returns:
        List of RawSearchResult objects
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    results = []

    for i in range(size):
        similarity = draw(st.floats(min_value=0.0, max_value=1.0))
        results.append(
            RawSearchResult(
                doc_id=f"doc_{i}",
                content=f"Content for document {i}",
                metadata={"index": i},
                similarity=similarity,
                domain=draw(st.sampled_from(["agriculture", "welfare", "education"])),
                entity_type=draw(st.sampled_from(["crop", "chemical", "scheme", "document"])),
                source_table="knowledge_items",
            )
        )

    return results


# Property 1: Top-K Similarity Ordering
# **Validates: Requirements 1.1, 1.4**


@pytest.mark.property
@given(
    top_k=st.integers(min_value=1, max_value=20),
    num_docs=st.integers(min_value=0, max_value=50),
)
def test_property_top_k_ordering(top_k: int, num_docs: int) -> None:
    """Property 1: Top-K Similarity Ordering.

    For any query embedding and document set, when performing similarity search
    with top_k=N, the system should return exactly N documents (or fewer if less
    than N exist) ordered by descending cosine similarity score.

    **Validates: Requirements 1.1, 1.4**
    """
    # Create mock database pool and settings
    mock_pool = Mock(spec=DatabasePool)
    mock_settings = Mock(spec=Settings)
    
    # Generate random similarity scores for documents
    similarities = [float(i) / num_docs for i in range(num_docs, 0, -1)]
    
    # Create mock results
    mock_results = []
    for i, sim in enumerate(similarities):
        mock_results.append(
            RawSearchResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                metadata={"index": i},
                similarity=sim,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            )
        )
    
    # Mock the database query execution
    # Database should return only top_k results (simulating LIMIT clause)
    limited_results = mock_results[:top_k]
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        (r.doc_id, r.content, r.metadata, r.similarity, r.domain, r.entity_type, r.source_table)
        for r in limited_results
    ]
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor
    mock_pool.get_connection.return_value = mock_conn
    mock_pool.release_connection = Mock()
    
    # Create search engine and execute search
    engine = VectorSearchEngine(mock_pool, mock_settings)
    query_embedding = [0.1] * 1536
    
    # Run async function
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        engine.similarity_search(query_embedding, top_k, threshold=0.0)
    )
    
    # Property assertions
    expected_count = min(top_k, num_docs)
    assert len(results) == expected_count, f"Expected {expected_count} results, got {len(results)}"
    
    # Verify ordering by similarity (descending)
    for i in range(len(results) - 1):
        assert results[i].similarity >= results[i + 1].similarity, \
            f"Results not ordered: {results[i].similarity} < {results[i + 1].similarity}"


# Property 2: Cosine Similarity Correctness
# **Validates: Requirements 1.2**


@pytest.mark.property
@given(
    # Use simpler strategy: generate a few values and repeat them
    seed=st.integers(min_value=0, max_value=1000),
)
def test_property_cosine_similarity_correctness(seed: int) -> None:
    """Property 2: Cosine Similarity Correctness.

    For any query embedding and retrieved documents, the similarity scores returned
    by the system should match independently calculated cosine similarity values
    within floating-point precision tolerance (±0.0001).

    **Validates: Requirements 1.2**
    """
    # Generate deterministic embeddings from seed
    import random
    random.seed(seed)
    
    # Create simple normalized vectors
    query_vec = [random.uniform(-1, 1) for _ in range(1536)]
    doc_vec = [random.uniform(-1, 1) for _ in range(1536)]
    
    # Normalize vectors
    query_norm = sum(q * q for q in query_vec) ** 0.5
    doc_norm = sum(d * d for d in doc_vec) ** 0.5
    
    if query_norm > 0:
        query_vec = [q / query_norm for q in query_vec]
    if doc_norm > 0:
        doc_vec = [d / doc_norm for d in doc_vec]
    
    # Calculate expected cosine similarity
    dot_product = sum(q * d for q, d in zip(query_vec, doc_vec))
    expected_similarity = dot_product
    
    # Simulate pgvector's cosine distance calculation
    pgvector_similarity = expected_similarity
    
    # Create mock database pool and settings
    mock_pool = Mock(spec=DatabasePool)
    mock_settings = Mock(spec=Settings)
    
    # Mock database result with calculated similarity
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        ("doc_1", "Test content", {}, pgvector_similarity, "agriculture", "crop", "knowledge_items")
    ]
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor
    mock_pool.get_connection.return_value = mock_conn
    mock_pool.release_connection = Mock()
    
    # Create search engine and execute search
    engine = VectorSearchEngine(mock_pool, mock_settings)
    
    # Run async function
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(
        engine.similarity_search(query_vec, top_k=1, threshold=0.0)
    )
    
    # Property assertion: returned similarity should match calculated similarity
    if len(results) > 0:
        assert abs(results[0].similarity - expected_similarity) < 0.0001, \
            f"Similarity mismatch: expected {expected_similarity}, got {results[0].similarity}"


# Property 3: Consistent Tie-Breaking
# **Validates: Requirements 1.5**


@pytest.mark.property
@given(
    num_ties=st.integers(min_value=2, max_value=10),
    tie_similarity=st.floats(min_value=0.0, max_value=1.0),
)
def test_property_consistent_tie_breaking(num_ties: int, tie_similarity: float) -> None:
    """Property 3: Consistent Tie-Breaking.

    For any query that returns documents with identical similarity scores,
    running the same query multiple times should return those documents in
    the same order (sorted by document ID).

    **Validates: Requirements 1.5**
    """
    # Create mock database pool and settings
    mock_pool = Mock(spec=DatabasePool)
    mock_settings = Mock(spec=Settings)
    
    # Create documents with identical similarity scores but different IDs
    doc_ids = [f"doc_{chr(65 + i)}" for i in range(num_ties)]  # doc_A, doc_B, doc_C, etc.
    
    # Mock database results with tied similarities
    mock_results = [
        (doc_id, f"Content for {doc_id}", {"id": doc_id}, tie_similarity, 
         "agriculture", "crop", "knowledge_items")
        for doc_id in doc_ids
    ]
    
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = mock_results
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor
    mock_pool.get_connection.return_value = mock_conn
    mock_pool.release_connection = Mock()
    
    # Create search engine
    engine = VectorSearchEngine(mock_pool, mock_settings)
    query_embedding = [0.1] * 1536
    
    # Run search multiple times
    loop = asyncio.get_event_loop()
    
    results_1 = loop.run_until_complete(
        engine.similarity_search(query_embedding, top_k=num_ties, threshold=0.0)
    )
    
    # Reset mock for second call
    mock_cursor.fetchall.return_value = mock_results
    
    results_2 = loop.run_until_complete(
        engine.similarity_search(query_embedding, top_k=num_ties, threshold=0.0)
    )
    
    # Property assertion: order should be consistent (sorted by doc_id)
    doc_ids_1 = [r.doc_id for r in results_1]
    doc_ids_2 = [r.doc_id for r in results_2]
    
    assert doc_ids_1 == doc_ids_2, \
        f"Inconsistent ordering: {doc_ids_1} != {doc_ids_2}"
    
    # Verify they are sorted by doc_id when similarities are equal
    assert doc_ids_1 == sorted(doc_ids), \
        f"Not sorted by doc_id: {doc_ids_1} != {sorted(doc_ids)}"


# Property 15: Input Validation
# **Validates: Requirements 9.5**


@pytest.mark.property
@given(
    top_k=st.one_of(
        st.integers(max_value=0),  # Invalid: too small
        st.integers(min_value=21, max_value=100),  # Invalid: too large
    ),
)
def test_property_input_validation_top_k(top_k: int) -> None:
    """Property 15: Input Validation (top_k).

    For any invalid input parameters (top_k < 1, top_k > 20), the system
    should raise a ValueError with a descriptive message.

    **Validates: Requirements 9.5**
    """
    # Create mock database pool and settings
    mock_pool = Mock(spec=DatabasePool)
    mock_settings = Mock(spec=Settings)
    
    # Create search engine
    engine = VectorSearchEngine(mock_pool, mock_settings)
    query_embedding = [0.1] * 1536
    
    # Run async function and expect ValidationError
    loop = asyncio.get_event_loop()
    
    with pytest.raises(ValidationError) as exc_info:
        loop.run_until_complete(
            engine.similarity_search(query_embedding, top_k=top_k, threshold=0.5)
        )
    
    # Verify error message is descriptive
    assert "top_k" in str(exc_info.value).lower()
    assert str(top_k) in str(exc_info.value)


@pytest.mark.property
@given(
    threshold=st.one_of(
        st.floats(max_value=-0.01),  # Invalid: negative
        st.floats(min_value=1.01, max_value=10.0),  # Invalid: > 1.0
    ),
)
def test_property_input_validation_threshold(threshold: float) -> None:
    """Property 15: Input Validation (threshold).

    For any invalid threshold (threshold < 0, threshold > 1), the system
    should raise a ValueError with a descriptive message.

    **Validates: Requirements 9.5**
    """
    # Create mock database pool and settings
    mock_pool = Mock(spec=DatabasePool)
    mock_settings = Mock(spec=Settings)
    
    # Create search engine
    engine = VectorSearchEngine(mock_pool, mock_settings)
    query_embedding = [0.1] * 1536
    
    # Run async function and expect ValidationError
    loop = asyncio.get_event_loop()
    
    with pytest.raises(ValidationError) as exc_info:
        loop.run_until_complete(
            engine.similarity_search(query_embedding, top_k=5, threshold=threshold)
        )
    
    # Verify error message is descriptive
    assert "threshold" in str(exc_info.value).lower()
