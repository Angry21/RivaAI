# Implementation Plan: Knowledge Base Retrieval System

## Overview

This plan implements the knowledge base retrieval system for RivaAI, enabling semantic search across agricultural, welfare, and education knowledge domains. The implementation uses PostgreSQL with pgvector for vector similarity search, OpenAI text-embedding-3-small for embeddings, and hybrid search (vector + keyword) for reranking. The system is designed for low-latency operation (<500ms) to support real-time voice conversations.

## Tasks

- [x] 1. Create core data models and exceptions
  - Create SearchResult dataclass with all required fields
  - Create RawSearchResult dataclass for pre-reranking results
  - Create custom exception classes (RetrievalError, EmbeddingError, DatabaseError, ValidationError)
  - Add type hints and docstrings following Google style
  - _Requirements: 2.4, 9.1_

- [x] 2. Implement VectorSearchEngine for pgvector similarity search
  - [x] 2.1 Create VectorSearchEngine class with database pool integration
    - Initialize with DatabasePool and Settings
    - Implement connection management using existing pool
    - Add logging configuration
    - _Requirements: 1.1, 5.3_

  - [x] 2.2 Implement similarity_search method with pgvector cosine distance
    - Use pgvector's <=> operator for cosine distance
    - Convert distance to similarity: similarity = 1 - distance
    - Support domain filtering with optional WHERE clause
    - Apply relevance threshold filtering
    - Return results ordered by similarity descending
    - Limit results to top_k
    - _Requirements: 1.1, 1.2, 2.2, 8.1_

  - [x] 2.3 Write property test for top-k similarity ordering
    - **Property 1: Top-K Similarity Ordering**
    - **Validates: Requirements 1.1, 1.4**

  - [x] 2.4 Write property test for cosine similarity correctness
    - **Property 2: Cosine Similarity Correctness**
    - **Validates: Requirements 1.2**

  - [x] 2.5 Write property test for consistent tie-breaking
    - **Property 3: Consistent Tie-Breaking**
    - **Validates: Requirements 1.5**

  - [x] 2.6 Add input validation for top_k and threshold parameters
    - Validate top_k is between 1 and 20
    - Validate threshold is between 0.0 and 1.0
    - Raise ValueError with descriptive messages for invalid inputs
    - _Requirements: 9.5_

  - [x] 2.7 Write property test for input validation
    - **Property 15: Input Validation**
    - **Validates: Requirements 9.5**

  - [x] 2.8 Implement retry logic for database connection failures
    - Retry up to 3 times with exponential backoff (100ms, 200ms, 400ms)
    - Log retry attempts with error details
    - Raise DatabaseError after exhausting retries
    - _Requirements: 9.2_

  - [x] 2.9 Write unit tests for error handling and edge cases
    - Test empty result sets
    - Test database connection failures with retry
    - Test invalid parameters
    - Test threshold filtering edge cases
    - _Requirements: 1.3, 9.2, 9.3_

- [x] 3. Implement HybridReranker for result reranking
  - [x] 3.1 Create HybridReranker class with configurable weights
    - Initialize with vector_weight (default 0.7) and keyword_weight (default 0.3)
    - Add settings for weight configuration
    - _Requirements: 4.1_

  - [x] 3.2 Implement keyword scoring using simple term overlap
    - Calculate keyword_score as: matched_terms / total_query_terms
    - Use case-insensitive matching
    - Handle empty queries gracefully
    - _Requirements: 4.1_

  - [x] 3.3 Implement rerank method with hybrid scoring
    - Calculate final_score = (vector_score * vector_weight) + (keyword_score * keyword_weight)
    - Preserve original similarity_score in results
    - Add reranked_score to results
    - Sort results by reranked_score descending
    - _Requirements: 4.1, 4.3_

  - [x] 3.4 Write property test for reranking score preservation
    - **Property 10: Reranking Score Preservation**
    - **Validates: Requirements 4.1, 4.3**

  - [x] 3.5 Implement fallback to vector-only ordering on reranking failure
    - Catch exceptions during keyword scoring
    - Log error with query details
    - Return results ordered by original similarity_score
    - _Requirements: 4.5_

  - [x] 3.6 Write unit test for reranking fallback behavior
    - Test fallback when keyword scoring fails
    - Verify error logging
    - Verify results use original ordering
    - _Requirements: 4.5_

- [x] 4. Checkpoint - Ensure search engine and reranker tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement RAGFormatter for context generation
  - [x] 5.1 Create RAGFormatter class with token estimation
    - Implement _estimate_tokens using 4 chars/token heuristic
    - Add configurable formatting template support
    - _Requirements: 7.3, 7.4_

  - [x] 5.2 Implement format_context method with token limit compliance
    - Format each document with header including domain and score
    - Add clear delimiters between documents (e.g., "---")
    - Truncate content to fit within max_tokens budget
    - Include document content, metadata, and relevance scores
    - _Requirements: 7.1, 7.2, 7.4, 7.5_

  - [x] 5.3 Write property test for RAG context structure
    - **Property 12: RAG Context Structure**
    - **Validates: Requirements 7.1, 7.2, 7.5**

  - [x] 5.4 Write property test for token limit compliance
    - **Property 13: Token Limit Compliance**
    - **Validates: Requirements 7.4**

  - [x] 5.5 Write unit tests for formatting edge cases
    - Test empty result list
    - Test single document
    - Test custom templates
    - Test truncation behavior
    - _Requirements: 7.3_

- [x] 6. Implement main RetrievalSystem interface
  - [x] 6.1 Create RetrievalSystem class integrating all components
    - Initialize with DatabasePool, EmbeddingGenerator, and Settings
    - Create instances of VectorSearchEngine, HybridReranker, and RAGFormatter
    - Configure latency thresholds from settings
    - _Requirements: 1.1, 2.1_

  - [x] 6.2 Implement search method with end-to-end retrieval flow
    - Validate input parameters (query, top_k, threshold)
    - Generate query embedding using EmbeddingGenerator
    - Perform vector similarity search using VectorSearchEngine
    - Apply hybrid reranking using HybridReranker
    - Apply relevance threshold filtering
    - Log metrics (query, result count, latency breakdown)
    - Return List[SearchResult]
    - _Requirements: 1.1, 2.1, 2.2, 4.1, 8.1, 10.1_

  - [x] 6.3 Write property test for unified interface coverage
    - **Property 4: Unified Interface Coverage**
    - **Validates: Requirements 2.1**

  - [x] 6.4 Write property test for domain filtering behavior
    - **Property 5: Domain Filtering Behavior**
    - **Validates: Requirements 2.2, 2.3**

  - [x] 6.5 Write property test for metadata completeness
    - **Property 6: Metadata Completeness**
    - **Validates: Requirements 2.4**

  - [x] 6.6 Write property test for entity-specific fields preservation
    - **Property 7: Entity-Specific Fields Preservation**
    - **Validates: Requirements 2.5**

  - [x] 6.7 Write property test for relevance threshold filtering
    - **Property 14: Relevance Threshold Filtering**
    - **Validates: Requirements 8.1, 8.2**

  - [x] 6.3 Implement latency monitoring and warning logs
    - Track embedding generation time
    - Track vector search time
    - Track reranking time
    - Track total end-to-end time
    - Log warning if total time exceeds 500ms threshold
    - Log warning if vector search exceeds 300ms threshold
    - Include timing breakdown in logs
    - _Requirements: 5.5, 10.1, 10.5_

  - [x] 6.9 Write unit tests for latency logging
    - Test warning logs for slow retrievals
    - Test metrics logging format
    - _Requirements: 5.5, 10.1_

- [x] 7. Implement batch retrieval functionality
  - [x] 7.1 Implement search_batch method for multiple queries
    - Generate embeddings in batch using EmbeddingGenerator.generate_embeddings_batch
    - Execute similarity searches for all queries
    - Apply reranking to each result set
    - Maintain query order correspondence
    - Return List[List[SearchResult]]
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 7.2 Write property test for batch query order correspondence
    - **Property 11: Batch Query Order Correspondence**
    - **Validates: Requirements 6.1, 6.4**

  - [x] 7.3 Implement partial failure handling for batch queries
    - Catch exceptions for individual queries
    - Continue processing remaining queries
    - Return empty list for failed queries
    - Log errors with query index and details
    - _Requirements: 6.5_

  - [x] 7.4 Write unit test for batch partial failure handling
    - Test with mix of valid and invalid queries
    - Verify partial results returned
    - Verify error logging
    - _Requirements: 6.5_

- [x] 8. Implement multi-language support features
  - [x] 8.1 Add support for local_names in searchable text
    - Ensure data loader includes local_names in content field
    - Verify local_names from all supported languages are indexed
    - _Requirements: 3.4_

  - [x] 8.2 Write property test for local names searchability
    - **Property 9: Local Names Searchability**
    - **Validates: Requirements 3.4**

  - [x] 8.3 Write property test for cross-language semantic matching
    - **Property 8: Cross-Language Semantic Matching**
    - **Validates: Requirements 3.2, 3.3**

  - [x] 8.4 Write unit tests for multi-language queries
    - Test queries in Hindi, Marathi, Telugu, Tamil, Bengali
    - Verify results are returned for all languages
    - _Requirements: 3.1_

- [x] 9. Checkpoint - Ensure all retrieval system tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Add comprehensive logging and metrics
  - [x] 10.1 Implement detailed retrieval metrics logging
    - Log query text (truncated to 100 chars)
    - Log number of results returned
    - Log latency breakdown (embedding, search, reranking, total)
    - Log similarity score distribution (min, max, mean)
    - Log number of documents filtered by threshold
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 10.2 Expose metrics for monitoring integration
    - Add latency metrics (p50, p95, p99) - structure only
    - Add error rate counters by type - structure only
    - Add query volume counters by domain - structure only
    - Note: Actual metrics collection integration deferred to monitoring setup
    - _Requirements: 10.4_

  - [x] 10.3 Write unit tests for logging and metrics
    - Test log message format and content
    - Test metrics structure
    - Test warning conditions
    - _Requirements: 10.1, 10.2, 10.4_

- [x] 11. Create module exports and initialization
  - [x] 11.1 Update rivaai/knowledge/__init__.py with exports
    - Export RetrievalSystem
    - Export SearchResult
    - Export custom exceptions
    - Add module docstring
    - _Requirements: 2.1_

  - [x] 11.2 Create retrieval.py module with all components
    - Organize imports following project conventions
    - Add module-level docstring
    - Ensure all type hints are complete
    - _Requirements: 2.1_

- [x] 12. Integration and documentation
  - [x] 12.1 Create usage example in examples/retrieval_example.py
    - Show basic search usage
    - Show batch search usage
    - Show RAG context formatting
    - Show error handling
    - _Requirements: 2.1, 6.1, 7.1_

  - [x] 12.2 Update settings.py with retrieval configuration
    - Verify embedding_model is set to "text-embedding-3-small"
    - Verify retrieval_relevance_threshold exists
    - Verify retrieval_top_k exists
    - Add any missing retrieval-related settings
    - _Requirements: 8.3_

  - [x] 12.3 Write integration tests with real database
    - Mark with @pytest.mark.integration
    - Test end-to-end retrieval with real PostgreSQL + pgvector
    - Test with real OpenAI API (requires test API key)
    - Test multi-language queries
    - Skip in CI/CD (requires external services)
    - _Requirements: 1.1, 2.1, 3.1_

- [x] 13. Final checkpoint - Run full test suite
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive testing and quality assurance
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 examples
- Unit tests validate specific examples, edge cases, and error conditions
- Integration tests require real database and API access (marked for manual testing)
- The system uses text-embedding-3-small (1536 dimensions) for optimal latency and cost
- Hybrid reranking uses simple keyword overlap (not BM25) to meet <50ms latency budget
- All async operations use existing DatabasePool and async OpenAI client
