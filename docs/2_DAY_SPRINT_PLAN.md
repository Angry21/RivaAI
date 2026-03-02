# RivaAI 2-Day Sprint Plan (MVP) - SERVERLESS ARCHITECTURE

## Goal: Working phone call with voice + knowledge retrieval in 48 hours

## What We're Building (MVP Only)

✅ User calls → System answers → User asks about wheat farming (Hindi) → System retrieves info → Responds with speech

❌ NOT building (post-MVP):
- Circuit breaker (safety) - use basic keyword filter only
- Barge-in - not critical for demo
- Session resumption - single session only
- PII masking - skip for demo
- Multi-domain knowledge - Wheat only
- Full testing - manual testing only

## NEW: Serverless Architecture (Lambda + API Gateway + DynamoDB + S3)

**Why this is better:**
- No servers to manage (no RDS, no Redis, no ECS)
- Faster deployment (deploy functions independently)
- Cheaper (~$5-10 per 1000 calls)
- Auto-scaling built-in

---

## Team Distribution (4 People, 2 Days)

### **DAY 1: Foundation (16 hours)**

#### **Person 1 (You) - API Gateway & Lambda Orchestration** [16 hours]
**Hour 0-4: AWS Infrastructure Setup**
- Create API Gateway (REST + WebSocket)
- Set up Lambda execution role with permissions
- Create Lambda layer with shared dependencies (boto3, etc.)
- Set up CloudWatch Logs for all functions

**Hour 4-8: Core Lambda Functions**
- Create `call-handler` Lambda (handles incoming calls)
- Create `audio-processor` Lambda (coordinates flow)
- Set up API Gateway → Lambda integrations
- Test with mock events

**Hour 8-12: Integration Orchestration**
- Wire Lambda functions together (async invocations)
- Set up environment variables for all functions
- Create simple keyword safety filter Lambda
- Test function-to-function communication

**Hour 12-16: End-to-End Testing**
- Deploy all functions
- Test API Gateway endpoints
- Fix integration issues
- Prepare for Day 2 polish

**Commands:**
```bash
# Create Lambda layer
cd lambda_layer
zip -r layer.zip .
aws lambda publish-layer-version --layer-name rivaai-common --zip-file fileb://layer.zip

# Deploy function
cd lambda_functions/call_handler
zip -r function.zip .
aws lambda create-function --function-name rivaai-call-handler --runtime python3.11 --handler handler.lambda_handler --zip-file fileb://function.zip
```

---

#### **Person 2 - DynamoDB & S3 Knowledge Base** [16 hours]
**Hour 0-4: DynamoDB Setup**
- Create `rivaai-sessions` table (session management)
- Create `rivaai-knowledge-index` table (vector search)
- Set up TTL for 24-hour auto-deletion
- Test read/write operations

**Hour 4-8: S3 Knowledge Base**
- Create `rivaai-knowledge-base` S3 bucket
- Prepare Wheat data as JSON files (1 crop, 2 chemicals, 1 scheme)
- Upload to S3 in organized structure
- Test S3 read operations

**Hour 8-12: Knowledge Retriever Lambda**
- Create `knowledge-retriever` Lambda function
- Read documents from S3
- Generate embeddings using Bedrock Titan
- Store embeddings in DynamoDB
- Implement simple vector search (cosine similarity)

**Hour 12-16: Integration & Testing**
- Test retrieval with Hindi queries
- Optimize DynamoDB queries
- Help Person 1 integrate retrieval Lambda
- Load test with sample data

**Sample S3 Structure:**
```
s3://rivaai-knowledge-base/
├── crops/wheat.json
├── chemicals/urea.json
└── schemes/pm-kisan.json
```

**Sample DynamoDB Item:**
```json
{
  "doc_id": "crop-wheat-001",
  "content": "Wheat cultivation requires...",
  "embedding": [0.123, -0.456, ...],
  "domain": "agriculture",
  "entity_type": "crop"
}
```

---

#### **Person 3 - Bedrock LLM Lambda Functions** [16 hours]
**Hour 0-4: Bedrock Setup & Testing**
- Enable Bedrock access in AWS account
- Test Claude 3 Haiku API calls
- Test Titan Embeddings V2
- Create sample prompts for Hindi

**Hour 4-8: Response Generator Lambda**
- Create `response-generator` Lambda function
- Implement Bedrock Claude 3 Haiku integration
- Build prompt template with RAG context injection
- Test with sample queries + context

**Hour 8-12: Intent Router Logic**
- Add simple intent detection (keyword matching)
- If "wheat/गेहूं" → trigger knowledge retrieval
- Otherwise → direct response
- Format responses for voice (short, simple)

**Hour 12-16: Integration & Prompt Tuning**
- Integrate with Person 1's orchestrator
- Test with Person 2's retrieval results
- Tune prompts for better Hindi responses
- Optimize response length (<50 words)

**Sample Lambda Handler:**
```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    query = event['query']
    rag_context = event.get('rag_context', '')
    
    prompt = f"Context: {rag_context}\n\nQuestion: {query}\n\nRespond in Hindi, keep it under 50 words."
    
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    
    return json.loads(response['body'].read())
```

---

#### **Person 4 - Speech Services & Telephony Lambda** [16 hours]
**Hour 0-4: Telephony Setup**
- Set up Exotel account (or Amazon Connect)
- Configure phone number
- Set up webhook pointing to API Gateway
- Test incoming call webhook

**Hour 4-8: Speech Synthesizer Lambda**
- Create `speech-synthesizer` Lambda function
- Implement AWS Polly integration (Aditi voice for Hindi)
- Handle text-to-speech conversion
- Return audio chunks

**Hour 8-12: Audio Processor Lambda**
- Create audio processing Lambda
- Implement AWS Transcribe streaming integration
- Handle audio format conversion (μ-law ↔ Linear16)
- Test with sample audio

**Hour 12-16: WebSocket Integration**
- Set up API Gateway WebSocket for audio streaming
- Connect WebSocket to Lambda functions
- Test real-time audio flow
- Fix audio quality issues

**Sample Polly Lambda:**
```python
import boto3
import base64

polly = boto3.client('polly', region_name='us-east-1')

def lambda_handler(event, context):
    text = event['text']
    
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='pcm',
        VoiceId='Aditi',  # Hindi voice
        Engine='neural',
        LanguageCode='hi-IN',
        SampleRate='16000'
    )
    
    audio_stream = response['AudioStream'].read()
    return {
        'statusCode': 200,
        'body': base64.b64encode(audio_stream).decode('utf-8')
    }
```

---

### **DAY 2: Integration & Polish (16 hours)**

#### **All Hands - Parallel Work**

**Hour 0-4: Integration Sprint**
- **Person 1**: Wire all components together
- **Person 2**: Fix any retrieval bugs
- **Person 3**: Optimize LLM prompts
- **Person 4**: Fix audio issues

**Hour 4-8: Testing & Bug Fixes**
- **Person 1**: Coordinate testing
- **Person 2**: Test knowledge retrieval accuracy
- **Person 3**: Test response quality
- **Person 4**: Test call quality

**Hour 8-12: Demo Preparation**
- **All**: Make 10 test calls
- **Person 1**: Document what works/doesn't
- **Person 2**: Prepare knowledge base stats
- **Person 3**: Prepare response examples
- **Person 4**: Ensure stable telephony

**Hour 12-16: Final Polish**
- **All**: Fix critical bugs only
- **Person 1**: Prepare demo script
- **Person 2-4**: Support as needed

---

## Simplified Architecture (MVP)

```
User Call (Exotel)
    ↓
AWS Transcribe (Hindi STT)
    ↓
Simple Intent Check (keyword match)
    ↓
If needs knowledge:
    → Vector Search (PostgreSQL + pgvector)
    → Claude 3 Haiku + RAG context
    ↓
AWS Polly (Hindi TTS)
    ↓
Response to User
```

---

## Critical Path (Must Work)

### Day 1 End Goals:
- [ ] Database with Wheat data loaded
- [ ] Bedrock returning Hindi responses
- [ ] Phone number answering calls
- [ ] Audio streaming working

### Day 2 End Goals:
- [ ] Complete call flow working
- [ ] Knowledge retrieval functional
- [ ] 1 successful demo call recorded

---

## What We're Cutting

1. **No Circuit Breaker** - Use basic keyword filter only
2. **No Barge-In** - User must wait for response
3. **No Session Management** - Each call is independent
4. **No PII Masking** - Don't store any data
5. **No Property Tests** - Manual testing only
6. **No Multi-Language** - Hindi only
7. **No Speech-to-Speech** - Too risky, use AWS Transcribe/Polly
8. **No Graph Traversal** - Simple vector search only
9. **No Hybrid Search** - Vector only
10. **No Multiple Domains** - Wheat farming only

---

## Risk Mitigation

### High Risk Items:
1. **Telephony Setup** (Person 4) - Start immediately, use Exotel (simpler than Amazon Connect)
2. **Audio Quality** (Person 4) - Test early, have backup plan
3. **Hindi Language** (All) - Test with native speaker

### Backup Plans:
- If Exotel fails → Use Twilio (even with India limitations)
- If AWS Transcribe fails → Use Deepgram
- If AWS Polly fails → Use ElevenLabs
- If Bedrock fails → Use OpenAI GPT-4

---

## Hourly Checkpoints

### Day 1
- **Hour 4**: Database running, Bedrock responding, Phone number active
- **Hour 8**: Retrieval working, LLM generating responses, Audio streaming
- **Hour 12**: All components individually tested
- **Hour 16**: Integration started

### Day 2
- **Hour 4**: End-to-end flow working (even if buggy)
- **Hour 8**: Major bugs fixed
- **Hour 12**: Demo-ready
- **Hour 16**: Polished and documented

---

## Communication Protocol

### Slack Channels:
- `#war-room` - All urgent issues
- `#blockers` - Immediate help needed
- `#wins` - Celebrate small victories

### Standups:
- **Every 4 hours** (Hour 0, 4, 8, 12, 16)
- 5 minutes max
- What's done? What's blocking?

### Pair Programming:
- Person 1 + Person 4 (Hour 8-12 Day 1) - Integration
- Person 2 + Person 3 (Hour 8-12 Day 1) - RAG integration

---

## Success Criteria (MVP)

### Must Have:
1. User calls phone number
2. System answers and greets in Hindi
3. User asks: "गेहूं की खेती के बारे में बताओ"
4. System retrieves wheat farming info
5. System responds with relevant info in Hindi
6. Call ends gracefully

### Nice to Have (if time):
2. Multiple test queries working
3. Error handling for bad audio
4. Fallback messages

---

## Post-MVP (After 2 Days)

Once MVP works, add in priority order:
1. Circuit breaker (safety) - Week 1
2. Session management - Week 1
3. Barge-in - Week 2
4. Multi-language - Week 2
5. More knowledge domains - Week 3
6. Speech-to-speech - Week 3
7. Full testing suite - Week 4

---

## Emergency Contacts

- AWS Support: Have account ready
- Exotel Support: Have number ready
- OpenAI Support: Backup for Bedrock
- Each other: Phone numbers shared

---

## Final Notes

**This is a SPRINT, not a marathon.**

- Work in parallel, integrate frequently
- Cut scope aggressively
- Manual testing is fine
- Hardcode values if needed
- Document assumptions
- Focus on ONE working demo

**If it works for 1 query, we can expand later.**

Good luck! 🚀
