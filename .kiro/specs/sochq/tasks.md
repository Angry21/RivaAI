# Implementation Plan: RivaAI - Cognitive Voice Interface for Decision Intelligence

## Overview

This implementation plan breaks down the RivaAI system into discrete coding tasks following the design document. The plan follows a phased approach prioritizing safety and core infrastructure before optimization. Each task builds incrementally, with checkpoints to validate functionality.

The implementation uses Python with FastAPI + uvloop for the backend (or Node.js/Go for Turn Manager), integrating with Twilio for telephony, Deepgram for STT, ElevenLabs for TTS, Groq API for fast LLM inference, and a unified PostgreSQL database with pgvector extension for knowledge storage.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Create Python project with FastAPI + uvloop backend (or Node.js/Go for Turn Manager)
  - Set up directory structure: `/telephony`, `/speech`, `/llm`, `/knowledge`, `/safety`, `/session`
  - Configure dependencies: FastAPI, WebSockets, Redis, async libraries, psycopg2, pgvector
  - Set up testing framework (pytest, Hypothesis for property-based testing)
  - Create configuration management for API keys and service endpoints
  - Set up AWS RDS Proxy and PostgreSQL connection pooling for 1000+ concurrent calls
  - _Requirements: All (foundational)_

- [x] 2. Implement Telephony Gateway and Audio Router
  - [x] 2.1 Create Twilio integration for call handling
    - Implement `TelephonyGateway` class with call lifecycle management
    - Handle incoming calls and establish WebSocket connections
    - Configure G.711 μ-law PCM audio format at 8kHz
    - Implement Audio Transcoding (G.711 µ-law → Linear16) within Turn Manager
    - _Requirements: 1.1, 1.4_
  
  - [x] 2.2 Write property test for call establishment latency
    - **Property 1: Call Establishment Latency**
    - **Validates: Requirements 1.1**
  
  - [x] 2.3 Implement Audio Router with bidirectional streaming
    - Create `AudioRouter` class managing incoming/outgoing audio streams
    - Implement audio chunk buffering with Redis Streams
    - Set up separate buffers for user and system audio
    - _Requirements: 1.1, 1.3_
  
  - [x] 2.4 Implement Barge-In Handler with VAD
    - Create `BargeInHandler` class with voice activity detection
    - Implement <300ms interrupt latency for system audio
    - Integrate WebRTC VAD or Silero VAD
    - _Requirements: 1.3_
  
  - [x] 2.5 Write property test for barge-in interrupt latency
    - **Property 3: Barge-In Interrupt Latency**
    - **Validates: Requirements 1.3**

- [x] 3. Checkpoint - Verify telephony and audio routing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Speech Processing components
  - [x] 4.1 Create Speech-to-Text Processor with streaming
    - Implement `SpeechProcessor` class integrating Deepgram Nova-2
    - Configure streaming recognition with partial results (<300ms latency)
    - Support all 5 Indian languages (hi-IN, mr-IN, te-IN, ta-IN, bn-IN)
    - Implement confidence scoring and low-confidence detection
    - Handle audio transcoding from G.711 µ-law to Linear16
    - _Requirements: 1.2, 2.1, 2.2, 2.4, 2.5_
  
  - [x] 4.2 Write property tests for STT latency and accuracy
    - **Property 2: Streaming STT Latency**
    - **Property 5: Noise Robustness**
    - **Property 6: Low Confidence Clarification**
    - **Property 8: Voice Activity Detection**
    - **Validates: Requirements 1.2, 2.1, 2.2, 2.4**
  
  - [x] 4.3 Create Text-to-Speech Processor with streaming
    - Implement `TextToSpeechProcessor` class integrating ElevenLabs Turbo
    - Configure streaming synthesis with <500ms first chunk latency
    - Support natural voices for all 5 languages
    - Output μ-law PCM at 8kHz for telephony
    - Implement Optimistic TTS Pipeline (Parallel Safety Check + Audio Buffering)
    - _Requirements: 1.5_
  
  - [x] 4.4 Write property test for TTS latency
    - **Property 4: Streaming TTS Latency**
    - **Validates: Requirements 1.5**
  
  - [x] 4.5 Implement language detection and DTMF fallback
    - Add language selection via DTMF when detection fails
    - Implement fallback to DTMF input mode for STT failures
    - _Requirements: 2.5, 8.1_

- [ ] 5. Implement Session Management with privacy preservation
  - [x] 5.1 Create Session Memory with Redis backend
    - Implement `SessionMemory` class with 24-hour TTL
    - Hash caller ANI using SHA-256 for privacy
    - Store conversation history and extracted entities
    - Implement automatic session expiration
    - _Requirements: 3.1, 3.3, 3.4_
  
  - [x] 5.2 Implement PII masking with NER
    - Create `mask_pii()` function using NER-based tokenization
    - Detect and mask names, phone numbers, addresses
    - Apply masking before storing any conversation data
    - _Requirements: 3.2_
  
  - [ ] 5.3 Write property tests for session management and privacy
    - **Property 9: Session Creation with TTL**
    - **Property 10: PII Masking**
    - **Property 11: Session Resumption**
    - **Property 13: Data Encryption and Purging**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
  
  - [ ] 5.4 Implement session resumption with user verification
    - Detect returning callers by hashed ANI
    - Prompt user to confirm identity for shared phones
    - Offer to resume or start fresh conversation
    - _Requirements: 3.6_
  
  - [ ] 5.5 Write property test for shared phone verification
    - **Property 14: Shared Phone Verification**
    - **Validates: Requirements 3.6**

- [ ] 6. Checkpoint - Verify speech processing and session management
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Knowledge Base with Unified PostgreSQL Store
  - [x] 7.1 Set up PostgreSQL with pgvector extension
    - Configure PostgreSQL database with pgvector extension
    - Create tables for farming, education, welfare domains with vector columns
    - Implement embedding generation using text-embedding-3-large
    - Set up AWS RDS Proxy for connection pooling
    - Create vector indexes using ivfflat for semantic search
    - _Requirements: 4.1, 4.2, 4.3, 4.6_
  
  - [ ] 7.2 Implement Relational Schema for graph relationships
    - Create entity tables (crops, chemicals, schemes, weather, institutions)
    - Define relationship tables using foreign keys (crop_chemical_relationships, etc.)
    - Load initial test data for Wheat domain
    - Validate foreign key constraints and relationships
    - _Requirements: 4.6_
  
  - [ ] 7.3 Implement Retrieval Layer with SQL-based hybrid search
    - Create `RetrievalLayer` class with PostgreSQL queries
    - Implement `hybrid_search()` using ORDER BY embedding <-> query_embedding
    - Implement `get_related_entities()` using JOIN-based graph traversal (2-hop limit)
    - Implement semantic caching with Redis (check cache before DB query)
    - Hybrid scoring: 0.6 * vector_score + 0.4 * relationship_score
    - _Requirements: 4.6_
  
  - [ ] 7.4 Write property test for graph-augmented retrieval
    - **Property 18: Graph-Augmented Retrieval**
    - **Validates: Requirements 4.6**
  
  - [ ] 7.5 Load verified knowledge for farming domain
    - Start with Wheat crop data and related entities
    - Add soil moisture, pesticide safety limits, weather data
    - Validate relationships are correctly established via foreign keys
    - _Requirements: 4.1_

- [ ] 8. Implement Circuit Breaker and Safety mechanisms (CRITICAL)
  - [ ] 8.1 Create Circuit Breaker with content scanning
    - Implement `CircuitBreaker` class with real-time content filtering
    - Create blacklist of high-risk keywords and patterns
    - Implement <100ms detection-to-halt latency
    - _Requirements: 5.3, 5.4_
  
  - [ ] 8.2 Create pre-recorded safety messages
    - Record safety messages in all 5 supported languages
    - Implement instant playback when circuit breaker triggers
    - Set up escalation to crisis support services
    - _Requirements: 5.3_
  
  - [ ] 8.3 Write property test for circuit breaker (CRITICAL)
    - **Property 21: Circuit Breaker Safety**
    - **Property 22: Blacklist Enforcement**
    - **Validates: Requirements 5.3, 5.4**
    - Test with adversarial inputs from TEST-04
  
  - [ ] 8.4 Implement Semantic Validator
    - Create `SemanticValidator` class for entity verification
    - Implement fuzzy matching against Knowledge Base
    - Add safety bounds checking for numeric values (dosages, amounts)
    - _Requirements: 2.3_
  
  - [ ] 8.5 Write property test for semantic validation
    - **Property 7: Critical Entity Validation**
    - **Validates: Requirements 2.3**
    - Test with out-of-bounds values from TEST-05

- [ ] 9. Checkpoint - Verify safety mechanisms
  - Ensure all safety tests pass, ask the user if questions arise.
  - CRITICAL: Circuit breaker must pass all adversarial tests before proceeding.

- [ ] 10. Implement Intent Router and LLM orchestration
  - [ ] 10.1 Create Intent Router with classification
    - Implement `IntentRouter` class with intent classification
    - Classify intents as GREETING, CLARIFICATION, or COMPLEX_DECISION
    - Route to appropriate handler (Groq API for simple, main LLM for complex)
    - Implement edge caching for common greetings
    - Implement semantic caching check (Redis) before RAG lookup
    - _Requirements: 10.1, 10.2, 10.3, 11.1, 11.3_
  
  - [ ] 10.2 Write property tests for intent-based latency
    - **Property 39: Simple Intent Latency**
    - **Property 40: Clarification Intent Latency**
    - **Property 41: Complex Decision Latency**
    - **Validates: Requirements 10.1, 10.2, 10.3**
  
  - [ ] 10.3 Integrate Groq API for fast LLM inference
    - Implement `SmallLanguageModel` class using Groq API (Llama 3.1 8B)
    - Configure for <500ms response generation
    - Implement filler generation during main LLM processing
    - Implement semantic caching in Redis for frequent patterns
    - _Requirements: 11.1, 11.2, 11.5_
  
  - [ ] 10.4 Write property tests for SLM coordination
    - **Property 43: SLM Filler Generation**
    - **Property 45: SLM-LLM Coordination**
    - **Property 46: SLM Coverage**
    - **Validates: Requirements 11.1, 11.3, 11.5**
  
  - [ ] 10.5 Implement speculative execution for RAG queries
    - Start query preparation on partial transcripts
    - Prevent premature response generation
    - _Requirements: 10.4_
  
  - [ ] 10.6 Write property test for speculative execution
    - **Property 42: Speculative Execution**
    - **Validates: Requirements 10.4**

- [ ] 11. Implement Conversation Brain (Main LLM)
  - [ ] 11.1 Create Conversation Brain with GPT-4/Claude integration
    - Implement `ConversationBrain` class with streaming LLM calls
    - Apply system prompt from requirements document
    - Implement entity extraction for domain-specific terms
    - Maintain conversation history in session context
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ] 11.2 Write property tests for conversation flow
    - **Property 24: Context Sufficiency Detection**
    - **Property 25: Single Question Clarification**
    - **Property 26: Single Clear Recommendation**
    - **Property 27: Continuation Offer**
    - **Validates: Requirements 6.2, 6.3, 6.4, 6.5**
  
  - [ ] 11.3 Implement [STOP_DANGER] token detection
    - Detect safety trigger token in LLM output
    - Immediately escalate to circuit breaker
    - _Requirements: 5.3_

- [ ] 12. Implement Decision Engine with RAG
  - [ ] 12.1 Create Decision Engine with retrieval integration
    - Implement `DecisionEngine` class coordinating retrieval and LLM
    - Integrate with Retrieval Layer for hybrid search
    - Generate responses using retrieved context
    - Implement confidence scoring using retrieval relevance and LLM confidence
    - _Requirements: 4.4, 4.5, 5.1, 5.2_
  
  - [ ] 12.2 Write property tests for RAG and confidence
    - **Property 16: RAG-Based Response Generation**
    - **Property 17: Retrieval Failure Handling**
    - **Property 19: Confidence Scoring**
    - **Property 20: Low Confidence Escalation**
    - **Validates: Requirements 4.4, 4.5, 5.1, 5.2**
  
  - [ ] 12.3 Implement domain-appropriate data source routing
    - Route farming queries to agricultural databases and weather APIs
    - Route education queries to scholarship databases
    - Route welfare queries to government scheme databases
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ] 12.4 Write property test for domain-appropriate sources
    - **Property 15: Domain-Appropriate Data Sources**
    - **Validates: Requirements 4.1, 4.2, 4.3**

- [ ] 13. Checkpoint - Verify LLM orchestration and RAG
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement Response Generator with constraints
  - [ ] 14.1 Create Response Generator with voice optimization
    - Implement `ResponseGenerator` class formatting for voice
    - Apply 40-token limit and <15 word sentences
    - Remove jargon and technical language
    - Add confidence disclaimers when needed
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ] 14.2 Write property tests for response quality
    - **Property 28: Actionable Decision Format**
    - **Property 29: Simple Language Constraint**
    - **Property 30: Specific Contact Information**
    - **Property 31: Response Length Constraint**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

- [ ] 15. Implement graceful degradation and error handling
  - [ ] 15.1 Implement fallback mechanisms for component failures
    - STT failure → DTMF fallback with voice prompts
    - Retrieval failure → cached knowledge with disclaimers
    - Low reliability → automatic human escalation offer
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ] 15.2 Write property tests for graceful degradation
    - **Property 32: STT Failure Fallback**
    - **Property 33: Retrieval Failure Fallback**
    - **Property 34: Low Reliability Auto-Escalation**
    - **Validates: Requirements 8.1, 8.2, 8.3**
  
  - [ ] 15.3 Implement privacy-preserving error logging
    - Log errors with context but no PII
    - Set up monitoring alerts for critical failures
    - _Requirements: 8.5_
  
  - [ ] 15.4 Write property test for privacy-preserving logging
    - **Property 35: Privacy-Preserving Error Logging**
    - **Validates: Requirements 8.5**

- [ ] 16. Implement human escalation pathways
  - [ ] 16.1 Create escalation system with context transfer
    - Implement human agent handoff with conversation context
    - Include confidence scores and extracted entities
    - Set up callback scheduling for unavailable agents
    - _Requirements: 5.2, 5.5_
  
  - [ ] 16.2 Write property test for escalation context transfer
    - **Property 23: Escalation Context Transfer**
    - **Validates: Requirements 5.5**

- [ ] 17. Implement privacy and data protection
  - [ ] 17.1 Implement post-call data deletion
    - Delete all PII after call ends
    - Retain only anonymized patterns
    - _Requirements: 9.1, 9.2_
  
  - [ ] 17.2 Write property tests for privacy compliance
    - **Property 36: Post-Call PII Deletion**
    - **Property 37: Audio Non-Persistence**
    - **Property 38: Data Encryption**
    - **Validates: Requirements 9.1, 9.2, 9.3**
  
  - [ ] 17.3 Implement encryption for all data paths
    - TLS for all network communication
    - AES-256 for data at rest in Redis
    - _Requirements: 9.3_

- [ ] 18. Checkpoint - Verify error handling and privacy
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Wire all components together into complete system
  - [ ] 19.1 Create main application orchestrator
    - Implement FastAPI application with WebSocket endpoints
    - Wire telephony → audio → speech → LLM → response → TTS pipeline
    - Integrate session management across all components
    - Set up async task coordination
    - _Requirements: All_
  
  - [ ] 19.2 Implement end-to-end call flow
    - Handle complete call lifecycle from answer to hangup
    - Coordinate all components for natural conversation
    - Implement conversation state machine
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ] 19.3 Write integration tests for end-to-end flows
    - Test complete conversations across all domains
    - Test error scenarios and recovery
    - Test barge-in during conversations
    - _Requirements: All_

- [ ] 20. Implement QA acceptance test scenarios
  - [ ] 20.1 Implement TEST-01: Rural Reality Stress Test (Noise)
    - Test with 85dB background noise (tractor scenario)
    - Verify correct intent extraction despite noise
    - _Requirements: 2.1_
  
  - [ ] 20.2 Implement TEST-02: Barge-In Stress Test
    - Test interruption during long system speech
    - Verify <300ms audio stop latency
    - _Requirements: 1.3_
  
  - [ ] 20.3 Implement TEST-03: Shared Phone Test
    - Test session resumption with different users
    - Verify identity confirmation prompt
    - _Requirements: 3.6_
  
  - [ ] 20.4 Implement TEST-04: Circuit Breaker Safety (CRITICAL)
    - Test with adversarial suicide-related query
    - Verify instant halt and safety message playback
    - _Requirements: 5.3_
  
  - [ ] 20.5 Implement TEST-05: Semantic Validator Test
    - Test with lethal pesticide dosage (50L/acre)
    - Verify out-of-bounds detection and correction
    - _Requirements: 2.3_
  
  - [ ] 20.6 Implement TEST-06: Latency Budget Test
    - Test complex query with RAG
    - Verify SLM filler within 500ms, final response within 3s
    - _Requirements: 10.3, 11.1_
  
  - [ ] 20.7 Implement TEST-07: Degradation Test
    - Simulate STT service crash
    - Verify automatic DTMF fallback
    - _Requirements: 8.1_

- [ ] 21. Final checkpoint - Complete system validation
  - Ensure all tests pass, ask the user if questions arise.
  - Verify all 7 QA acceptance tests pass consistently.
  - Verify all 46 correctness properties pass with 100+ iterations each.

- [ ] 22. Performance optimization and load testing
  - [ ] 22.1 Optimize latency-critical paths
    - Profile and optimize STT/TTS pipelines
    - Optimize retrieval query performance
    - Implement caching for frequent queries
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [ ] 22.2 Conduct load testing
    - Test with 1000 concurrent calls
    - Verify latency requirements under load
    - Test auto-scaling behavior
    - _Requirements: 10.5_
  
  - [ ] 22.3 Implement monitoring and observability
    - Set up distributed tracing for latency analysis
    - Create dashboards for call metrics
    - Configure alerts for circuit breaker triggers and errors
    - _Requirements: 8.5_

- [ ] 23. Expand knowledge base beyond initial Wheat domain
  - [ ] 23.1 Add additional crops and farming knowledge
    - Expand to 5-10 common crops with relationships
    - Add regional weather data integration
    - Add more chemical safety data
    - _Requirements: 4.1_
  
  - [ ] 23.2 Add education domain knowledge
    - Load scholarship databases
    - Add institutional information
    - Create graph relationships for eligibility
    - _Requirements: 4.2_
  
  - [ ] 23.3 Add welfare scheme knowledge
    - Load government scheme data
    - Add eligibility criteria and application processes
    - Create graph relationships for user profiles
    - _Requirements: 4.3_

- [ ] 24. Final production readiness validation
  - Verify all items in Production Readiness Checklist from requirements
  - Conduct security audit of circuit breaker and privacy mechanisms
  - Verify all 7 QA test scenarios pass consistently
  - Verify Graph-Augmented Vector Store populated with verified data
  - Verify latency requirements validated under 1000 concurrent calls
  - Verify human escalation pathways configured and tested

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at critical milestones
- Property tests validate universal correctness properties (100+ iterations each)
- Unit tests validate specific examples, edge cases, and integration points
- Safety tests (Circuit Breaker, Semantic Validator) are CRITICAL and must pass before any user-facing deployment
- The implementation follows a phased approach: Infrastructure → Safety → Knowledge → Optimization → Scale
- Start with single domain (Wheat in farming) before expanding to full knowledge base
- Architecture uses unified PostgreSQL + pgvector (not separate Neo4j + Qdrant)
- Speech services: Deepgram Nova-2 (STT) and ElevenLabs Turbo (TTS) for low latency
- LLM: Groq API for fast inference (<500ms) instead of self-hosted Llama
- Database: AWS RDS Proxy with connection pooling for 1000+ concurrent calls
