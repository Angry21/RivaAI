"""Unit tests for RAG context formatter."""

import pytest

from rivaai.knowledge.models import SearchResult
from rivaai.knowledge.rag_formatter import RAGFormatter


def test_format_empty_results():
    """Test formatting empty result list."""
    formatter = RAGFormatter()
    context = formatter.format_context([], max_tokens=2000)
    
    assert context == "", "Empty results should produce empty context"


def test_format_single_document():
    """Test formatting a single document."""
    formatter = RAGFormatter()
    
    result = SearchResult(
        doc_id="doc1",
        content="This is a test document about wheat farming.",
        metadata={"name": "Wheat"},
        similarity_score=0.95,
        reranked_score=0.92,
        domain="agriculture",
        entity_type="crop",
        source_table="crops",
    )
    
    context = formatter.format_context([result], max_tokens=2000)
    
    assert "Document 1" in context
    assert "agriculture" in context
    assert "crop" in context
    assert "0.9200" in context  # Reranked score
    assert "wheat farming" in context
    assert "---" in context


def test_format_multiple_documents():
    """Test formatting multiple documents."""
    formatter = RAGFormatter()
    
    results = [
        SearchResult(
            doc_id="doc1",
            content="Wheat information",
            metadata={},
            similarity_score=0.95,
            reranked_score=0.92,
            domain="agriculture",
            entity_type="crop",
            source_table="crops",
        ),
        SearchResult(
            doc_id="doc2",
            content="Rice information",
            metadata={},
            similarity_score=0.90,
            reranked_score=0.88,
            domain="agriculture",
            entity_type="crop",
            source_table="crops",
        ),
    ]
    
    context = formatter.format_context(results, max_tokens=2000)
    
    assert "Document 1" in context
    assert "Document 2" in context
    assert "Wheat information" in context
    assert "Rice information" in context


def test_format_with_custom_template():
    """Test formatting with custom template."""
    formatter = RAGFormatter()
    
    result = SearchResult(
        doc_id="doc1",
        content="Test content",
        metadata={},
        similarity_score=0.95,
        reranked_score=None,
        domain="agriculture",
        entity_type="crop",
        source_table="crops",
    )
    
    custom_template = "Doc {index}: {content} (Score: {score})\n"
    context = formatter.format_context([result], max_tokens=2000, template=custom_template)
    
    assert "Doc 1:" in context
    assert "Test content" in context
    assert "Score:" in context


def test_format_truncation_behavior():
    """Test that documents are truncated when exceeding token budget."""
    formatter = RAGFormatter()
    
    # Create a document with long content
    long_content = "A" * 2000  # 2000 characters
    result = SearchResult(
        doc_id="doc1",
        content=long_content,
        metadata={},
        similarity_score=0.95,
        reranked_score=0.92,
        domain="agriculture",
        entity_type="crop",
        source_table="crops",
    )
    
    # Set small token budget
    context = formatter.format_context([result], max_tokens=100)
    
    # Context should be truncated
    assert len(context) < len(long_content)
    assert "[truncated]" in context or len(context) <= 100 * 4  # 4 chars per token


def test_format_uses_similarity_score_when_no_reranked():
    """Test that similarity score is used when reranked score is None."""
    formatter = RAGFormatter()
    
    result = SearchResult(
        doc_id="doc1",
        content="Test content",
        metadata={},
        similarity_score=0.85,
        reranked_score=None,
        domain="agriculture",
        entity_type="crop",
        source_table="crops",
    )
    
    context = formatter.format_context([result], max_tokens=2000)
    
    assert "0.8500" in context  # Should use similarity_score


def test_format_multiple_documents_with_budget_limit():
    """Test that only documents fitting in budget are included."""
    formatter = RAGFormatter()
    
    results = [
        SearchResult(
            doc_id=f"doc{i}",
            content="X" * 500,  # 500 chars each
            metadata={},
            similarity_score=0.9,
            reranked_score=0.9,
            domain="agriculture",
            entity_type="crop",
            source_table="crops",
        )
        for i in range(10)
    ]
    
    # Small budget should limit number of documents
    context = formatter.format_context(results, max_tokens=200)
    
    # Should have fewer than 10 documents
    doc_count = context.count("Document ")
    assert doc_count < 10, "Should not include all documents when budget is tight"


def test_estimate_tokens():
    """Test token estimation method."""
    formatter = RAGFormatter()
    
    text = "A" * 400  # 400 characters
    tokens = formatter._estimate_tokens(text)
    
    assert tokens == 100, "Should estimate 100 tokens for 400 chars (4 chars/token)"


def test_format_preserves_document_order():
    """Test that documents are formatted in the order provided."""
    formatter = RAGFormatter()
    
    results = [
        SearchResult(
            doc_id=f"doc{i}",
            content=f"Content {i}",
            metadata={},
            similarity_score=0.9 - i * 0.1,
            reranked_score=None,
            domain="agriculture",
            entity_type="crop",
            source_table="crops",
        )
        for i in range(3)
    ]
    
    context = formatter.format_context(results, max_tokens=5000)
    
    # Check order
    pos_0 = context.find("Content 0")
    pos_1 = context.find("Content 1")
    pos_2 = context.find("Content 2")
    
    assert pos_0 < pos_1 < pos_2, "Documents should appear in provided order"

