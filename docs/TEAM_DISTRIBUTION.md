# RivaAI Team Task Distribution

## Team Structure (4 People)

Based on your current progress and remaining tasks, here's the optimal distribution:

---

## **Person 1 (You) - Tech Lead & Integration**

**Focus**: System integration, architecture decisions, and critical path items

### Responsibilities:
1. **Session Management & Privacy** (Task 5)
   - Implement PII masking with NER
   - Session resumption logic
   - Privacy compliance testing
   - **Priority**: HIGH (foundational for safety)

2. **Circuit Breaker & Safety** (Task 8) - CRITICAL
   - Content scanning and blacklist enforcement
   - Safety message playback
   - Adversarial testing
   - **Priority**: CRITICAL (must work before any deployment)

3. **System Integration** (Task 19)
   - Wire all components together
   - End-to-end call flow orchestration
   - Component coordination
   - **Priority**: HIGH (blocks deployment)

4. **Team Coordination**
   - Code reviews
   - Architecture decisions
   - Blocker resolution
   - Daily standups

**Estimated Time**: 3-4 weeks

---

## **Person 2 - Knowledge Base & RAG Specialist**

**Focus**: Knowledge infrastructure and retrieval systems

### Responsibilities:
1. **Knowledge Base Setup** (Task 7)
   - PostgreSQL with pgvector configuration
   - Relational schema for graph relationships
   - Initial data loading (Wheat domain)
   - Vector index optimization
   - **Priority**: HIGH (needed for RAG)

2. **Retrieval Layer** (Task 7.3)
   - SQL-based hybrid search implementation
   - Graph traversal with JOINs
   - Semantic caching with Redis
   - Performance optimization
   - **Priority**: HIGH

3. **Knowledge Base Expansion** (Task 23)
   - Add more crops (5-10 common ones)
   - Education domain data
   - Welfare schemes data
   - Regional weather integration
   - **Priority**: MEDIUM (post-MVP)

4. **Testing**
   - Property tests for retrieval
   - Integration tests with real data
   - Performance benchmarks

**Estimated Time**: 3-4 weeks

---

## **Person 3 - LLM & Conversation Management**

**Focus**: LLM integration, conversation flow, and decision engine

### Responsibilities:
1. **Intent Router** (Task 10)
   - Intent classification logic
   - Routing to appropriate LLM (Haiku vs Sonnet)
   - Edge caching for greetings
   - Speculative execution
   - **Priority**: HIGH

2. **Conversation Brain** (Task 11)
   - AWS Bedrock integration (Claude 3.5)
   - Entity extraction
   - Conversation history management
   - System prompt implementation
   - **Priority**: HIGH

3. **Decision Engine with RAG** (Task 12)
   - Coordinate retrieval + LLM
   - Confidence scoring
   - Domain-appropriate routing
   - Response generation
   - **Priority**: HIGH

4. **Response Generator** (Task 14)
   - Voice optimization (40 tokens, <15 words)
   - Confidence disclaimers
   - Simple language enforcement
   - **Priority**: MEDIUM

**Estimated Time**: 3-4 weeks

---

## **Person 4 - Speech & Telephony Integration**

**Focus**: Speech processing, telephony, and audio pipeline

### Responsibilities:
1. **Speech-to-Speech Integration** (NEW)
   - Complete OpenAI Realtime API integration
   - Hybrid processor implementation
   - RAG context injection
   - Multi-language voice mapping
   - **Priority**: HIGH (core differentiator)

2. **AWS Speech Services** (Task 4 extension)
   - AWS Transcribe streaming integration
   - AWS Polly TTS implementation
   - Audio format conversion (μ-law ↔ Linear16)
   - Latency optimization
   - **Priority**: HIGH

3. **Telephony Gateway** (Task 2 extension)
   - Amazon Connect integration
   - Exotel integration (backup)
   - WebSocket/streaming setup
   - Call lifecycle management
   - **Priority**: HIGH

4. **Audio Router & Barge-In** (Task 2.3, 2.4)
   - Bidirectional audio streaming
   - VAD integration
   - Barge-in handler (<300ms latency)
   - **Priority**: MEDIUM

**Estimated Time**: 3-4 weeks

---

## Parallel Work Streams

### Week 1-2: Foundation
- **Person 1**: Session management + PII masking
- **Person 2**: PostgreSQL setup + initial data load
- **Person 3**: Bedrock client integration + basic LLM calls
- **Person 4**: Speech-to-speech basic integration

### Week 2-3: Core Features
- **Person 1**: Circuit breaker implementation + testing
- **Person 2**: Retrieval layer + hybrid search
- **Person 3**: Intent router + conversation brain
- **Person 4**: AWS Transcribe/Polly + telephony gateways

### Week 3-4: Integration & Testing
- **Person 1**: System integration + end-to-end flow
- **Person 2**: Knowledge base expansion + optimization
- **Person 3**: Decision engine + RAG integration
- **Person 4**: Audio pipeline optimization + barge-in

### Week 4+: Polish & Deploy
- **All**: QA testing, bug fixes, performance optimization
- **Person 1**: Deployment coordination
- **Person 2**: Data validation
- **Person 3**: Prompt tuning
- **Person 4**: Latency optimization

---

## Critical Path (Must Complete in Order)

1. **Week 1**: 
   - PostgreSQL + pgvector setup (Person 2)
   - Bedrock integration (Person 3)
   - Session management (Person 1)

2. **Week 2**:
   - Retrieval layer working (Person 2)
   - LLM responding (Person 3)
   - Speech-to-speech basic flow (Person 4)

3. **Week 3**:
   - Circuit breaker operational (Person 1) - CRITICAL
   - RAG + LLM integrated (Person 2 + Person 3)
   - Telephony connected (Person 4)

4. **Week 4**:
   - End-to-end call working (Person 1)
   - All components integrated
   - Testing complete

---

## Dependencies Map

```
Person 2 (Knowledge Base)
    ↓
Person 3 (LLM + RAG) ← Person 1 (Session + Safety)
    ↓
Person 4 (Speech + Telephony)
    ↓
Person 1 (Integration)
```

---

## Communication Protocol

### Daily Standups (15 min)
- What did you complete yesterday?
- What are you working on today?
- Any blockers?

### Weekly Sync (1 hour)
- Demo working features
- Review integration points
- Adjust priorities

### Slack/Discord Channels
- `#general` - Team coordination
- `#knowledge-base` - Person 2 updates
- `#llm-rag` - Person 3 updates
- `#speech-telephony` - Person 4 updates
- `#integration` - Person 1 updates
- `#blockers` - Urgent issues

---

## Success Metrics

### Week 1
- [ ] PostgreSQL with pgvector running
- [ ] Bedrock returning responses
- [ ] Session creation working
- [ ] Speech-to-speech test call

### Week 2
- [ ] Knowledge retrieval working
- [ ] LLM + RAG integrated
- [ ] PII masking functional
- [ ] AWS Transcribe/Polly working

### Week 3
- [ ] Circuit breaker blocking harmful content
- [ ] Intent routing working
- [ ] Telephony gateway connected
- [ ] Barge-in functional

### Week 4
- [ ] End-to-end call successful
- [ ] All tests passing
- [ ] Latency requirements met
- [ ] Ready for deployment

---

## Risk Mitigation

### High Risk Items
1. **Circuit Breaker** - Must work perfectly (Person 1 priority)
2. **Speech-to-Speech** - New technology (Person 4 needs support)
3. **RAG Integration** - Complex coordination (Person 2 + 3 sync daily)

### Mitigation Strategies
- Person 1 reviews all safety-critical code
- Person 4 has fallback to AWS Transcribe/Polly
- Person 2 and 3 pair program on RAG integration

---

## Tools & Setup

### Required Access
- AWS account with Bedrock, RDS, ElastiCache access
- OpenAI API key (for speech-to-speech)
- Amazon Connect or Exotel account
- GitHub repository access
- Shared development environment

### Development Environment
- Local PostgreSQL + Redis (docker-compose)
- Shared staging environment on AWS
- Individual feature branches
- CI/CD pipeline for testing

---

## Notes

- **Person 1 (You)** handles critical path and integration - most experienced
- **Person 2** can work independently on knowledge base
- **Person 3** needs coordination with Person 2 for RAG
- **Person 4** has most external dependencies (APIs, telephony)

This distribution balances workload, minimizes dependencies, and ensures critical safety features are handled by the tech lead.
