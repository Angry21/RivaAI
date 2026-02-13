"""RAG context formatter for LLM prompt injection."""

import logging
from typing import List, Optional

from rivaai.knowledge.models import SearchResult

logger = logging.getLogger(__name__)


class RAGFormatter:
    """Formats search results for RAG context injection into LLM prompts.
    
    Converts search results into structured context strings suitable for
    LLM consumption, with token budget management and customizable templates.
    """

    DEFAULT_TEMPLATE = """
Document {index} (Domain: {domain}, Type: {entity_type}, Score: {score:.4f})
Source: {source_table}
---
{content}
---
"""

    def __init__(self) -> None:
        """Initialize RAG formatter."""
        logger.info("RAGFormatter initialized")

    def format_context(
        self,
        results: List[SearchResult],
        max_tokens: int = 2000,
        template: Optional[str] = None,
    ) -> str:
        """Format search results as LLM context string.
        
        Formats results with clear delimiters and metadata, respecting token
        budget constraints. Documents are included in order until token budget
        is exhausted.
        
        Args:
            results: Search results to format
            max_tokens: Maximum token budget (approximate, using 4 chars/token)
            template: Optional custom formatting template (uses DEFAULT_TEMPLATE if None)
            
        Returns:
            Formatted context string with document delimiters
        """
        if not results:
            return ""
        
        template_str = template or self.DEFAULT_TEMPLATE
        max_chars = max_tokens * 4  # Approximate: 4 chars per token
        
        formatted_docs = []
        current_chars = 0
        
        for idx, result in enumerate(results, start=1):
            # Use reranked score if available, otherwise similarity score
            score = result.reranked_score if result.reranked_score is not None else result.similarity_score
            
            # Format document using template
            doc_str = template_str.format(
                index=idx,
                domain=result.domain,
                entity_type=result.entity_type,
                score=score,
                source_table=result.source_table,
                content=result.content,
            )
            
            # Check if adding this document would exceed budget
            doc_chars = len(doc_str)
            if current_chars + doc_chars > max_chars:
                # Try to fit truncated version
                remaining_chars = max_chars - current_chars
                if remaining_chars > 200:  # Only truncate if we have reasonable space
                    truncated_content = result.content[:remaining_chars - 150] + "... [truncated]"
                    doc_str = template_str.format(
                        index=idx,
                        domain=result.domain,
                        entity_type=result.entity_type,
                        score=score,
                        source_table=result.source_table,
                        content=truncated_content,
                    )
                    formatted_docs.append(doc_str)
                    logger.info(
                        f"Truncated document {idx} to fit token budget "
                        f"({self._estimate_tokens(doc_str)} tokens)"
                    )
                break
            
            formatted_docs.append(doc_str)
            current_chars += doc_chars
        
        context = "\n".join(formatted_docs)
        
        logger.info(
            f"Formatted {len(formatted_docs)} documents into context "
            f"(~{self._estimate_tokens(context)} tokens, {len(context)} chars)"
        )
        
        return context

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using 4 chars/token heuristic.
        
        This is a rough approximation. Actual token count depends on the
        tokenizer used by the LLM.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        return len(text) // 4

