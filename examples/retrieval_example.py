"""Example usage of the knowledge base retrieval system.

This example demonstrates:
1. Basic search usage
2. Batch search usage
3. RAG context formatting
4. Error handling
"""

import asyncio
import logging

from rivaai.config.database import get_database_pool
from rivaai.config.settings import get_settings
from rivaai.knowledge import RetrievalSystem, get_embedding_generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def basic_search_example():
    """Demonstrate basic search functionality."""
    logger.info("=== Basic Search Example ===")
    
    # Initialize dependencies
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    # Create retrieval system
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    # Perform search
    query = "What are the best crops for monsoon season?"
    logger.info(f"Query: {query}")
    
    try:
        results = await retrieval.search(
            query=query,
            domain="agriculture",  # Optional domain filter
            top_k=5,
            threshold=0.7,  # Optional relevance threshold
        )
        
        logger.info(f"Found {len(results)} results")
        
        for i, result in enumerate(results, 1):
            logger.info(f"\nResult {i}:")
            logger.info(f"  Doc ID: {result.doc_id}")
            logger.info(f"  Domain: {result.domain}")
            logger.info(f"  Type: {result.entity_type}")
            logger.info(f"  Similarity: {result.similarity_score:.4f}")
            logger.info(f"  Reranked: {result.reranked_score:.4f}")
            logger.info(f"  Content: {result.content[:100]}...")
        
    except Exception as e:
        logger.error(f"Search failed: {e}")


async def batch_search_example():
    """Demonstrate batch search functionality."""
    logger.info("\n=== Batch Search Example ===")
    
    # Initialize dependencies
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    # Create retrieval system
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    # Multiple queries
    queries = [
        "What fertilizers are safe for wheat?",
        "Government schemes for farmers",
        "Best practices for rice cultivation",
    ]
    
    logger.info(f"Processing {len(queries)} queries in batch")
    
    try:
        results_list = await retrieval.search_batch(
            queries=queries,
            domain=None,  # Search all domains
            top_k=3,
        )
        
        for i, (query, results) in enumerate(zip(queries, results_list), 1):
            logger.info(f"\nQuery {i}: {query}")
            logger.info(f"  Results: {len(results)}")
            
            for j, result in enumerate(results, 1):
                logger.info(f"    {j}. {result.entity_type} - {result.similarity_score:.4f}")
        
    except Exception as e:
        logger.error(f"Batch search failed: {e}")


async def rag_formatting_example():
    """Demonstrate RAG context formatting."""
    logger.info("\n=== RAG Context Formatting Example ===")
    
    # Initialize dependencies
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    # Create retrieval system
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    # Perform search
    query = "How to protect crops from pests?"
    
    try:
        results = await retrieval.search(query=query, top_k=3)
        
        # Format for RAG
        context = await retrieval.format_for_rag(
            results=results,
            max_tokens=2000,  # Token budget for LLM context
        )
        
        logger.info(f"Generated RAG context ({len(context)} chars):")
        logger.info(f"\n{context[:500]}...")  # Show first 500 chars
        
    except Exception as e:
        logger.error(f"RAG formatting failed: {e}")


async def error_handling_example():
    """Demonstrate error handling."""
    logger.info("\n=== Error Handling Example ===")
    
    # Initialize dependencies
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    # Create retrieval system
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    # Test various error conditions
    
    # 1. Empty query
    try:
        await retrieval.search(query="", top_k=5)
    except Exception as e:
        logger.info(f"Empty query error (expected): {type(e).__name__}: {e}")
    
    # 2. Invalid top_k
    try:
        await retrieval.search(query="test", top_k=0)
    except Exception as e:
        logger.info(f"Invalid top_k error (expected): {type(e).__name__}: {e}")
    
    # 3. Invalid threshold
    try:
        await retrieval.search(query="test", threshold=1.5)
    except Exception as e:
        logger.info(f"Invalid threshold error (expected): {type(e).__name__}: {e}")
    
    logger.info("Error handling examples completed")


async def domain_filtering_example():
    """Demonstrate domain filtering."""
    logger.info("\n=== Domain Filtering Example ===")
    
    # Initialize dependencies
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    # Create retrieval system
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    query = "What support is available?"
    
    # Search different domains
    domains = ["agriculture", "welfare", "education", None]
    
    for domain in domains:
        try:
            results = await retrieval.search(
                query=query,
                domain=domain,
                top_k=3,
            )
            
            domain_name = domain or "all"
            logger.info(f"\nDomain '{domain_name}': {len(results)} results")
            
            for result in results:
                logger.info(f"  - {result.domain}/{result.entity_type}")
        
        except Exception as e:
            logger.error(f"Search failed for domain {domain}: {e}")


async def main():
    """Run all examples."""
    try:
        await basic_search_example()
        await batch_search_example()
        await rag_formatting_example()
        await error_handling_example()
        await domain_filtering_example()
        
        logger.info("\n=== All examples completed successfully ===")
        
    except Exception as e:
        logger.error(f"Example execution failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

