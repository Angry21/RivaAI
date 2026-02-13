"""Unit tests for HybridReranker.

Tests error handling, edge cases, and specific scenarios.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from rivaai.config.settings import Settings
from rivaai.knowledge.models import RawSearchResult, SearchResult
from rivaai.knowledge.reranker import HybridReranker


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return Mock(spec=Settings)


@pytest.fixture
def reranker(mock_settings):
    """Create HybridReranker instance."""
    return HybridReranker(mock_settings)


@pytest.fixture
def sample_results():
    """Create sample raw search results."""
    return [
        RawSearchResult(
            doc_id="doc_1",
            content="wheat crop information for farmers",
            metadata={"type": "crop"},
            similarity=0.9,
            domain="agriculture",
            entity_type="crop",
            source_table="knowledge_items",
        ),
        RawSearchResult(
            doc_id="doc_2",
            content="rice cultivation guide",
            metadata={"type": "crop"},
            similarity=0.8,
            domain="agriculture",
            entity_type="crop",
            source_table="knowledge_items",
        ),
        RawSearchResult(
            doc_id="doc_3",
            content="fertilizer application methods",
            metadata={"type": "chemical"},
            similarity=0.7,
            domain="agriculture",
            entity_type="chemical",
            source_table="knowledge_items",
        ),
    ]


class TestBasicReranking:
    """Test basic reranking functionality."""

    @pytest.mark.asyncio
    async def test_rerank_returns_search_results(self, reranker, sample_results):
        """Test that rerank converts RawSearchResult to SearchResult."""
        query = "wheat farming"
        results = await reranker.rerank(query, sample_results)

        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_rerank_preserves_original_similarity(self, reranker, sample_results):
        """Test that original similarity scores are preserved."""
        query = "wheat farming"
        results = await reranker.rerank(query, sample_results)

        # Check that original similarities are preserved
        assert results[0].similarity_score in [0.9, 0.8, 0.7]
        assert results[1].similarity_score in [0.9, 0.8, 0.7]
        assert results[2].similarity_score in [0.9, 0.8, 0.7]

    @pytest.mark.asyncio
    async def test_rerank_adds_reranked_score(self, reranker, sample_results):
        """Test that reranked scores are added to results."""
        query = "wheat farming"
        results = await reranker.rerank(query, sample_results)

        # All results should have reranked scores
        assert all(r.reranked_score is not None for r in results)
        assert all(0.0 <= r.reranked_score <= 1.0 for r in results)

    @pytest.mark.asyncio
    async def test_rerank_orders_by_reranked_score(self, reranker, sample_results):
        """Test that results are ordered by reranked score descending."""
        query = "wheat farming"
        results = await reranker.rerank(query, sample_results)

        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i].reranked_score >= results[i + 1].reranked_score

    @pytest.mark.asyncio
    async def test_rerank_empty_list(self, reranker):
        """Test that empty result list returns empty list."""
        query = "test query"
        results = await reranker.rerank(query, [])

        assert results == []
        assert isinstance(results, list)


class TestKeywordScoring:
    """Test keyword scoring functionality."""

    @pytest.mark.asyncio
    async def test_keyword_score_boosts_matching_terms(self, reranker):
        """Test that documents with matching keywords get boosted."""
        results = [
            RawSearchResult(
                doc_id="doc_1",
                content="wheat crop farming guide",
                metadata={},
                similarity=0.5,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
            RawSearchResult(
                doc_id="doc_2",
                content="unrelated content about something else",
                metadata={},
                similarity=0.5,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
        ]

        query = "wheat farming"
        reranked = await reranker.rerank(query, results)

        # doc_1 should be ranked higher due to keyword matches
        assert reranked[0].doc_id == "doc_1"
        assert reranked[0].reranked_score > reranked[1].reranked_score

    def test_keyword_score_jaccard_similarity(self, reranker):
        """Test Jaccard similarity calculation."""
        # Test exact match
        score = reranker._keyword_score("wheat farming", "wheat farming")
        assert score == 1.0

        # Test partial match
        score = reranker._keyword_score("wheat farming", "wheat crop farming guide")
        # Intersection: {wheat, farming} = 2
        # Union: {wheat, farming, crop, guide} = 4
        # Jaccard: 2/4 = 0.5
        assert score == 0.5

        # Test no match
        score = reranker._keyword_score("wheat farming", "rice cultivation")
        assert score == 0.0

    def test_keyword_score_case_insensitive(self, reranker):
        """Test that keyword scoring is case insensitive."""
        score1 = reranker._keyword_score("Wheat Farming", "wheat farming")
        score2 = reranker._keyword_score("wheat farming", "WHEAT FARMING")

        assert score1 == 1.0
        assert score2 == 1.0

    def test_keyword_score_empty_query(self, reranker):
        """Test that empty query returns 0.0."""
        score = reranker._keyword_score("", "some document content")
        assert score == 0.0

    def test_keyword_score_empty_document(self, reranker):
        """Test that empty document returns 0.0."""
        score = reranker._keyword_score("query text", "")
        assert score == 0.0


class TestFallbackBehavior:
    """Test fallback to vector-only ordering on errors."""

    @pytest.mark.asyncio
    async def test_fallback_on_keyword_scoring_failure(
        self, reranker, mock_settings, sample_results
    ):
        """Test fallback when keyword scoring fails."""
        # Patch _keyword_score to raise an exception
        with patch.object(
            reranker, "_keyword_score", side_effect=Exception("Keyword scoring failed")
        ):
            query = "test query"
            results = await reranker.rerank(query, sample_results)

            # Should still return results
            assert len(results) == 3
            assert all(isinstance(r, SearchResult) for r in results)

            # Should be ordered by original similarity (descending)
            assert results[0].similarity_score == 0.9
            assert results[1].similarity_score == 0.8
            assert results[2].similarity_score == 0.7

            # Reranked scores should equal similarity scores (fallback)
            for result in results:
                assert result.reranked_score == result.similarity_score

    @pytest.mark.asyncio
    async def test_fallback_logs_error(self, reranker, sample_results, caplog):
        """Test that fallback logs error message."""
        # Patch _keyword_score to raise an exception
        with patch.object(
            reranker, "_keyword_score", side_effect=Exception("Test error")
        ):
            query = "test query"
            await reranker.rerank(query, sample_results)

            # Check that error was logged
            assert any("Reranking failed" in record.message for record in caplog.records)
            assert any(
                "Falling back to vector-only ordering" in record.message
                for record in caplog.records
            )

    @pytest.mark.asyncio
    async def test_fallback_preserves_all_fields(self, reranker, sample_results):
        """Test that fallback preserves all result fields."""
        # Patch _keyword_score to raise an exception
        with patch.object(
            reranker, "_keyword_score", side_effect=Exception("Test error")
        ):
            query = "test query"
            results = await reranker.rerank(query, sample_results)

            # Verify all fields are preserved
            for i, result in enumerate(results):
                original = sample_results[i]
                assert result.doc_id == original.doc_id
                assert result.content == original.content
                assert result.metadata == original.metadata
                assert result.domain == original.domain
                assert result.entity_type == original.entity_type
                assert result.source_table == original.source_table


class TestCustomWeights:
    """Test custom weight configuration."""

    @pytest.mark.asyncio
    async def test_custom_weights_initialization(self, mock_settings):
        """Test reranker with custom weights."""
        reranker = HybridReranker(
            mock_settings, vector_weight=0.6, keyword_weight=0.4
        )

        assert reranker.vector_weight == 0.6
        assert reranker.keyword_weight == 0.4

    @pytest.mark.asyncio
    async def test_vector_only_weight(self, mock_settings):
        """Test reranker with vector-only weight (keyword_weight=0)."""
        reranker = HybridReranker(
            mock_settings, vector_weight=1.0, keyword_weight=0.0
        )

        results = [
            RawSearchResult(
                doc_id="doc_1",
                content="wheat farming guide",
                metadata={},
                similarity=0.9,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
            RawSearchResult(
                doc_id="doc_2",
                content="rice cultivation",
                metadata={},
                similarity=0.8,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
        ]

        query = "wheat"
        reranked = await reranker.rerank(query, results)

        # With vector_weight=1.0, order should match original similarity
        assert reranked[0].doc_id == "doc_1"
        assert reranked[1].doc_id == "doc_2"
        assert reranked[0].reranked_score == 0.9
        assert reranked[1].reranked_score == 0.8

    @pytest.mark.asyncio
    async def test_keyword_only_weight(self, mock_settings):
        """Test reranker with keyword-only weight (vector_weight=0)."""
        reranker = HybridReranker(
            mock_settings, vector_weight=0.0, keyword_weight=1.0
        )

        results = [
            RawSearchResult(
                doc_id="doc_1",
                content="unrelated content",
                metadata={},
                similarity=0.9,  # High vector similarity
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
            RawSearchResult(
                doc_id="doc_2",
                content="wheat farming guide",
                metadata={},
                similarity=0.5,  # Lower vector similarity
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
        ]

        query = "wheat farming"
        reranked = await reranker.rerank(query, results)

        # With keyword_weight=1.0, doc_2 should rank higher due to keyword match
        assert reranked[0].doc_id == "doc_2"
        assert reranked[0].reranked_score > reranked[1].reranked_score


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_single_result(self, reranker):
        """Test reranking with single result."""
        results = [
            RawSearchResult(
                doc_id="doc_1",
                content="test content",
                metadata={},
                similarity=0.8,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            )
        ]

        query = "test"
        reranked = await reranker.rerank(query, results)

        assert len(reranked) == 1
        assert reranked[0].doc_id == "doc_1"
        assert reranked[0].reranked_score is not None

    @pytest.mark.asyncio
    async def test_identical_similarities(self, reranker):
        """Test reranking with identical similarity scores."""
        results = [
            RawSearchResult(
                doc_id="doc_1",
                content="wheat farming",
                metadata={},
                similarity=0.8,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
            RawSearchResult(
                doc_id="doc_2",
                content="rice cultivation",
                metadata={},
                similarity=0.8,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            ),
        ]

        query = "wheat"
        reranked = await reranker.rerank(query, results)

        # doc_1 should rank higher due to keyword match
        assert reranked[0].doc_id == "doc_1"
        assert reranked[0].reranked_score > reranked[1].reranked_score

    @pytest.mark.asyncio
    async def test_very_long_content(self, reranker):
        """Test reranking with very long document content."""
        long_content = " ".join(["word"] * 10000)
        results = [
            RawSearchResult(
                doc_id="doc_1",
                content=long_content,
                metadata={},
                similarity=0.8,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            )
        ]

        query = "test query"
        reranked = await reranker.rerank(query, results)

        assert len(reranked) == 1
        assert reranked[0].reranked_score is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, reranker):
        """Test reranking with special characters in query."""
        results = [
            RawSearchResult(
                doc_id="doc_1",
                content="test content",
                metadata={},
                similarity=0.8,
                domain="agriculture",
                entity_type="crop",
                source_table="knowledge_items",
            )
        ]

        query = "test@#$%^&*()query"
        reranked = await reranker.rerank(query, results)

        assert len(reranked) == 1
        assert reranked[0].reranked_score is not None
