"""Verify knowledge base setup and test retrieval functionality."""

import asyncio
import logging

from rivaai.config.database import get_database_pool
from rivaai.config.settings import get_settings
from rivaai.knowledge import RetrievalSystem, get_embedding_generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def verify_database():
    """Verify database tables and data."""
    logger.info("=== Verifying Database ===")
    
    settings = get_settings()
    db_pool = get_database_pool(settings)
    
    conn = db_pool.get_connection()
    try:
        with conn.cursor() as cursor:
            # Check tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('crops', 'chemicals', 'schemes', 'knowledge_items')
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if len(tables) == 4:
                logger.info(f"✓ All required tables exist: {', '.join(tables)}")
            else:
                logger.error(f"✗ Missing tables. Found: {', '.join(tables)}")
                return False
            
            # Check data counts
            cursor.execute("SELECT COUNT(*) FROM crops")
            crop_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chemicals")
            chemical_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM schemes")
            scheme_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM knowledge_items")
            knowledge_count = cursor.fetchone()[0]
            
            logger.info(f"✓ Data counts:")
            logger.info(f"  - Crops: {crop_count}")
            logger.info(f"  - Chemicals: {chemical_count}")
            logger.info(f"  - Schemes: {scheme_count}")
            logger.info(f"  - Knowledge Items: {knowledge_count}")
            
            if knowledge_count == 0:
                logger.warning("⚠ No data in knowledge_items table. Run load_knowledge_base.py")
                return False
            
            # Check embeddings
            cursor.execute("SELECT COUNT(*) FROM knowledge_items WHERE embedding IS NOT NULL")
            embedding_count = cursor.fetchone()[0]
            
            if embedding_count == knowledge_count:
                logger.info(f"✓ All {embedding_count} items have embeddings")
            else:
                logger.warning(f"⚠ Only {embedding_count}/{knowledge_count} items have embeddings")
            
            # Check pgvector extension
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            if cursor.fetchone():
                logger.info("✓ pgvector extension is installed")
            else:
                logger.error("✗ pgvector extension not found")
                return False
            
            return True
            
    finally:
        db_pool.release_connection(conn)


async def test_retrieval():
    """Test retrieval functionality."""
    logger.info("\n=== Testing Retrieval ===")
    
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    # Test queries
    test_queries = [
        ("What crops are good for monsoon?", "agriculture"),
        ("Tell me about fertilizers", "agriculture"),
        ("Government schemes for farmers", "welfare"),
    ]
    
    for query, domain in test_queries:
        logger.info(f"\nQuery: '{query}' (domain: {domain})")
        
        try:
            results = await retrieval.search(
                query=query,
                domain=domain,
                top_k=3,
                threshold=0.5,
            )
            
            if results:
                logger.info(f"✓ Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    logger.info(
                        f"  {i}. {result.entity_type} - "
                        f"similarity={result.similarity_score:.3f}, "
                        f"reranked={result.reranked_score:.3f}"
                    )
                    logger.info(f"     {result.content[:80]}...")
            else:
                logger.warning(f"⚠ No results found")
                
        except Exception as e:
            logger.error(f"✗ Query failed: {e}")
            return False
    
    return True


async def test_rag_formatting():
    """Test RAG context formatting."""
    logger.info("\n=== Testing RAG Formatting ===")
    
    settings = get_settings()
    db_pool = get_database_pool(settings)
    embedding_gen = get_embedding_generator(settings)
    
    retrieval = RetrievalSystem(db_pool, embedding_gen, settings)
    
    try:
        # Get some results
        results = await retrieval.search(
            query="wheat farming",
            top_k=2,
            threshold=0.5,
        )
        
        if not results:
            logger.warning("⚠ No results to format")
            return True
        
        # Format for RAG
        context = await retrieval.format_for_rag(results, max_tokens=500)
        
        if context:
            logger.info(f"✓ Generated RAG context ({len(context)} chars)")
            logger.info(f"Preview:\n{context[:200]}...")
            return True
        else:
            logger.error("✗ RAG formatting returned empty context")
            return False
            
    except Exception as e:
        logger.error(f"✗ RAG formatting failed: {e}")
        return False


async def main():
    """Run all verification tests."""
    logger.info("=" * 60)
    logger.info("RivaAI Knowledge Base Verification")
    logger.info("=" * 60)
    
    try:
        # Verify database
        db_ok = await verify_database()
        if not db_ok:
            logger.error("\n✗ Database verification failed")
            return
        
        # Test retrieval
        retrieval_ok = await test_retrieval()
        if not retrieval_ok:
            logger.error("\n✗ Retrieval test failed")
            return
        
        # Test RAG formatting
        rag_ok = await test_rag_formatting()
        if not rag_ok:
            logger.error("\n✗ RAG formatting test failed")
            return
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ All verification tests passed!")
        logger.info("=" * 60)
        logger.info("\nKnowledge base is ready to use.")
        logger.info("Next steps:")
        logger.info("  1. Add more domain-specific data")
        logger.info("  2. Integrate with LLM for RAG responses")
        logger.info("  3. Connect to telephony for voice queries")
        
    except Exception as e:
        logger.error(f"\n✗ Verification failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
