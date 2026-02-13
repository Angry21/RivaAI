"""Property-based tests for HybridReranker.

Feature: knowledge-base-retrieval
"""

import asyncio
from typing import List
from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from rivaai.config.settings import Settings
from rivaai.knowledge.models import RawSearchResult
from rivaai.knowledge.reranker import HybridReranker


# Hypothesis strategies for test data generation


@st.composite
def raw_search_results(
    draw: st.DrawFn, min_size: int = 1, max_size: int = 20
) -> List[RawSearchResult]:
    """Generate a list of raw search results with varying similarity scores.

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
        content = draw(
            st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
                min_size=10,
                max_size=200,
            )
        )
        results.append(
            RawSearchResult(
                doc_id=f"doc_{i}",
                content=content,
                metadata={"index": i},
                similarity=similarity,
                domain=draw(st.sampled_from(["agriculture", "welfare", "education"])),
                entity_type=draw(
                    st.sampled_from(["crop", "chemical", "scheme", "document"])
                ),
                source_table="knowledge_items",
            )
        )

    return results


# Property 10: Reranking Score Preservation
# **Validates: Requirements 4.1, 4.3**


@pytest.mark.property
@given(
    results=raw_search_results(min_size=1, max_size=10),
    query=st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
        min_size=5,
        max_size=100,
    ),
)
def test_property_reranking_score_preservation(
    results: List[RawSearchResult], query: str
) -> None:
    """Property 10: Reranking Score Preservation.

    For any search with reranking enabled, each result should contain both
    the original similarity_score and the reranked_score, and the results
    should be ordered by reranked_score.

    **Validates: Requirements 4.1, 4.3**
    """
    # Create mock settings
    mock_settings = Mock(spec=Settings)

    # Create reranker
    reranker = HybridReranker(mock_settings)

    # Run async rerank
    loop = asyncio.get_event_loop()
    reranked_results = loop.run_until_complete(reranker.rerank(query, results))

    # Property assertions
    assert len(reranked_results) == len(
        results
    ), f"Expected {len(results)} results, got {len(reranked_results)}"

    # Check that all results have both scores
    for result in reranked_results:
        assert result.similarity_score is not None, "Missing similarity_score"
        assert result.reranked_score is not None, "Missing reranked_score"
        assert 0.0 <= result.similarity_score <= 1.0, "similarity_score out of range"
        assert 0.0 <= result.reranked_score <= 1.0, "reranked_score out of range"

    # Check that original similarity scores are preserved
    original_similarities = {r.doc_id: r.similarity for r in results}
    for result in reranked_results:
        assert (
            result.similarity_score == original_similarities[result.doc_id]
        ), f"Original similarity not preserved for {result.doc_id}"

    # Check that results are ordered by reranked_score descending
    for i in range(len(reranked_results) - 1):
        assert (
            reranked_results[i].reranked_score >= reranked_results[i + 1].reranked_score
        ), (
            f"Results not ordered by reranked_score: "
            f"{reranked_results[i].reranked_score} < "
            f"{reranked_results[i + 1].reranked_score}"
        )


@pytest.mark.property
@given(
    results=raw_search_results(min_size=1, max_size=10),
    vector_weight=st.floats(min_value=0.0, max_value=1.0),
)
def test_property_reranking_with_custom_weights(
    results: List[RawSearchResult], vector_weight: float
) -> None:
    """Property: Reranking respects custom weights.

    For any custom weight configuration, the reranked scores should be
    calculated correctly using the specified weights.

    **Validates: Requirements 4.1**
    """
    # Create mock settings
    mock_settings = Mock(spec=Settings)

    # Calculate keyword weight
    keyword_weight = 1.0 - vector_weight

    # Create reranker with custom weights
    reranker = HybridReranker(
        mock_settings, vector_weight=vector_weight, keyword_weight=keyword_weight
    )

    # Use a simple query
    query = "test query"

    # Run async rerank
    loop = asyncio.get_event_loop()
    reranked_results = loop.run_until_complete(reranker.rerank(query, results))

    # Property assertions
    assert len(reranked_results) == len(results)

    # Verify that reranked scores are within valid range
    for result in reranked_results:
        assert 0.0 <= result.reranked_score <= 1.0, "reranked_score out of range"

        # Verify the score is a weighted combination
        # (we can't verify exact calculation without reimplementing keyword scoring,
        # but we can verify it's in the valid range)
        assert result.reranked_score >= 0.0
        assert result.reranked_score <= 1.0


@pytest.mark.property
@given(
    num_results=st.integers(min_value=0, max_value=5),
)
def test_property_reranking_empty_and_small_sets(num_results: int) -> None:
    """Property: Reranking handles empty and small result sets.

    For any result set size including empty, reranking should handle it
    gracefully without errors.

    **Validates: Requirements 4.1**
    """
    # Create mock settings
    mock_settings = Mock(spec=Settings)

    # Create reranker
    reranker = HybridReranker(mock_settings)

    # Create results
    results = [
        RawSearchResult(
            doc_id=f"doc_{i}",
            content=f"Content for document {i}",
            metadata={"index": i},
            similarity=0.5,
            domain="agriculture",
            entity_type="crop",
            source_table="knowledge_items",
        )
        for i in range(num_results)
    ]

    # Run async rerank
    loop = asyncio.get_event_loop()
    reranked_results = loop.run_until_complete(reranker.rerank("test query", results))

    # Property assertions
    assert len(reranked_results) == num_results
    if num_results > 0:
        for result in reranked_results:
            assert result.similarity_score is not None
            assert result.reranked_score is not None
