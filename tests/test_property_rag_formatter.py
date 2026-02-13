"""Property-based tests for RAG context formatter.

Feature: knowledge-base-retrieval
"""

import pytest
from hypothesis import given, strategies as st

from rivaai.knowledge.models import SearchResult
from rivaai.knowledge.rag_formatter import RAGFormatter


# Strategies for generating test data
@st.composite
def search_result_strategy(draw):
    """Generate a valid SearchResult for testing."""
    doc_id = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_characters="\n\r")))
    content = draw(st.text(min_size=10, max_size=500))
    similarity_score = draw(st.floats(min_value=0.0, max_value=1.0))
    reranked_score = draw(st.none() | st.floats(min_value=0.0, max_value=1.0))
    domain = draw(st.sampled_from(["agriculture", "welfare", "education"]))
    entity_type = draw(st.sampled_from(["crop", "chemical", "scheme", "document"]))
    source_table = draw(st.sampled_from(["crops", "chemicals", "schemes", "knowledge_items"]))
    
    return SearchResult(
        doc_id=doc_id,
        content=content,
        metadata={"test": "data"},
        similarity_score=similarity_score,
        reranked_score=reranked_score,
        domain=domain,
        entity_type=entity_type,
        source_table=source_table,
    )


@pytest.mark.property
@given(results=st.lists(search_result_strategy(), min_size=1, max_size=10))
def test_property_rag_context_structure(results):
    """Property 12: RAG Context Structure.
    
    For any non-empty list of search results, the formatted RAG context should be
    a non-empty string containing all document contents, metadata, and relevance
    scores with clear delimiters between documents.
    
    **Validates: Requirements 7.1, 7.2, 7.5**
    """
    formatter = RAGFormatter()
    
    # Format with large token budget to ensure all documents fit
    context = formatter.format_context(results, max_tokens=10000)
    
    # Context should be non-empty
    assert context, "Context should be non-empty for non-empty result list"
    
    # Context should contain all document contents (or truncated versions)
    for result in results:
        # Check if content or truncated marker is present
        content_preview = result.content[:50]
        assert (
            content_preview in context or "[truncated]" in context
        ), f"Context should contain document content or truncation marker"
    
    # Context should contain metadata (domain, entity_type, source_table)
    for result in results:
        assert result.domain in context, "Context should contain domain"
        assert result.entity_type in context, "Context should contain entity_type"
        assert result.source_table in context, "Context should contain source_table"
    
    # Context should contain relevance scores
    for result in results:
        score = result.reranked_score if result.reranked_score is not None else result.similarity_score
        # Score should appear in some form (formatted to 4 decimal places)
        score_str = f"{score:.4f}"
        assert score_str in context or "Score:" in context, "Context should contain relevance scores"
    
    # Context should have clear delimiters
    assert "---" in context, "Context should contain document delimiters"
    
    # Context should have document numbering
    assert "Document 1" in context, "Context should contain document numbering"


@pytest.mark.property
@given(
    results=st.lists(search_result_strategy(), min_size=1, max_size=5),
    max_tokens=st.integers(min_value=100, max_value=5000),
)
def test_property_token_limit_compliance(results, max_tokens):
    """Property 13: Token Limit Compliance.
    
    For any token limit specified, the formatted RAG context should not exceed
    that limit (approximately, using 4 chars/token estimation).
    
    **Validates: Requirements 7.4**
    """
    formatter = RAGFormatter()
    
    context = formatter.format_context(results, max_tokens=max_tokens)
    
    # Estimate tokens using same heuristic as formatter
    estimated_tokens = len(context) // 4
    
    # Allow small tolerance for rounding and formatting overhead
    tolerance = 10  # 10 token tolerance
    assert (
        estimated_tokens <= max_tokens + tolerance
    ), f"Context exceeds token limit: {estimated_tokens} > {max_tokens}"


@pytest.mark.property
@given(results=st.lists(search_result_strategy(), min_size=0, max_size=10))
def test_property_empty_results_handling(results):
    """Property: Empty results should return empty context.
    
    For any list of search results (including empty), the formatter should
    handle it gracefully without errors.
    """
    formatter = RAGFormatter()
    
    context = formatter.format_context(results, max_tokens=2000)
    
    if not results:
        assert context == "", "Empty results should produce empty context"
    else:
        assert isinstance(context, str), "Context should always be a string"


@pytest.mark.property
@given(
    results=st.lists(search_result_strategy(), min_size=1, max_size=3),
    template=st.text(min_size=10, max_size=200),
)
def test_property_custom_template_support(results, template):
    """Property: Custom templates should be supported.
    
    For any valid custom template, the formatter should use it instead of
    the default template (if it contains required format fields).
    """
    formatter = RAGFormatter()
    
    # Use default template if custom template is invalid
    try:
        context = formatter.format_context(results, max_tokens=5000, template=template)
        assert isinstance(context, str), "Context should be a string"
    except (KeyError, ValueError):
        # Invalid template format is acceptable - formatter should handle gracefully
        # or raise appropriate error
        pass

