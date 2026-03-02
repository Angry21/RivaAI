# RivaAI AWS Architecture (Using Required Services)

## Architecture Overview

```
User Call (Exotel/Amazon Connect)
    ↓
API Gateway (WebSocket + REST)
    ↓
Lambda Functions (Serverless)
    ↓
├─ DynamoDB (Session State)
├─ S3 (Knowledge Base Documents)
├─ Bedrock (LLM + Embeddings)
├─ Transcribe (STT)
└─ Polly (TTS)
```

---

## Service Mapping

### **API Gateway** - Entry Point
**Use for:**
- REST API endpoints for webhooks
- WebSocket API for real-time audio streaming
- Request routing to Lambda functions

**Endpoints:**
- `POST /webhooks/call` - Incoming call webhook
- `WS /audio` - WebSocket for audio streaming
- `POST /api/query` - Direct query API (testing)

---

### **Lambda Functions** - Compute Layer

**Function 1: `call-handler`**
- Handles incoming call events
- Creates session in DynamoDB
- Triggers audio processing
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 60 seconds

**Function 2: `audio-processor`**
- Processes audio chunks
- Calls Transcribe for STT
- Routes to knowledge retrieval
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 300 seconds

**Function 3: `knowledge-retriever`**
- Retrieves from S3 knowledge base
- Generates embeddings via Bedrock
- Performs vector search
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 30 seconds

**Function 4: `response-generator`**
- Takes query + RAG context
- Calls Bedrock (Claude)
- Generates response text
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 30 seconds

**Function 5: `speech-synthesizer`**
- Takes response text
- Calls Polly for TTS
- Returns audio chunks
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 30 seconds

---

### **DynamoDB** - Session & State Management

**Table 1: `rivaai-sessions`**
```
Partition Key: session_id (String)
Sort Key: timestamp (Number)

Attributes:
- session_id: UUID
- caller_number_hash: String (SHA-256)
- language_code: String (hi-IN, etc.)
- conversation_history: List
- created_at: Number (Unix timestamp)
- ttl: Number (24 hours from creation)
- status: String (active, ended)
```

**Table 2: `rivaai-knowledge-index`**
```
Partition Key: doc_id (String)

Attributes:
- doc_id: UUID
- content: String
- embedding: List (1024 floats for Titan V2)
- metadata: Map
- domain: String (agriculture, welfare, education)
- entity_type: String (crop, chemical, scheme)
```

**Why DynamoDB instead of PostgreSQL:**
- ✅ Serverless (no management)
- ✅ Auto-scaling
- ✅ Built-in TTL (24-hour data retention)
- ✅ Fast key-value lookups
- ✅ Works perfectly with Lambda

---

### **S3** - Knowledge Base Storage

**Bucket: `rivaai-knowledge-base`**

**Structure:**
```
rivaai-knowledge-base/
├── crops/
│   ├── wheat.json
│   ├── rice.json
│   └── cotton.json
├── chemicals/
│   ├── urea.json
│   └── dap.json
├── schemes/
│   ├── pm-kisan.json
│   └── fasal-bima.json
└── embeddings/
    └── index.json (pre-computed embeddings)
```

**Sample Document (wheat.json):**
```json
{
  "id": "crop-wheat-001",
  "name": "Wheat",
  "local_names": {
    "hi": "गेहूं",
    "mr": "गहू"
  },
  "content": "Wheat cultivation requires well-drained loamy soil...",
  "embedding": [0.123, -0.456, ...],
  "metadata": {
    "season": "Rabi",
    "region": "North India"
  }
}
```

**Why S3 instead of RDS:**
- ✅ Serverless (no database to manage)
- ✅ Cheaper for read-heavy workloads
- ✅ Easy to update knowledge base (just upload JSON)
- ✅ Works great with Lambda
- ✅ Can use S3 Select for queries

---

### **ECS** - Long-Running Services (Optional)

**Use ECS Fargate for:**
- WebSocket connection manager (if API Gateway WebSocket isn't enough)
- Audio streaming coordinator
- Real-time processing that exceeds Lambda limits

**Service: `rivaai-audio-coordinator`**
- Manages long-duration calls (>15 minutes)
- Handles WebSocket connections
- Coordinates between Lambda functions
- **Only needed if calls exceed Lambda timeout**

**For 2-day MVP: Skip ECS, use Lambda only**

---

### **EC2** - Not Needed for MVP

**Skip EC2 for now because:**
- Lambda handles all compute
- DynamoDB handles state
- S3 handles storage
- No need for persistent servers

**Use EC2 later for:**
- Custom speech models
- High-throughput processing
- Cost optimization (if Lambda gets expensive)

---

### **Amplify** - Frontend (Optional)

**Use Amplify for:**
- Admin dashboard to manage knowledge base
- Testing interface for queries
- Analytics dashboard

**For 2-day MVP: Skip Amplify, use AWS Console**

---

## Simplified 2-Day Architecture

### **Day 1: Core Services**

```
API Gateway (REST)
    ↓
Lambda: call-handler
    ↓
DynamoDB: sessions table
    ↓
Lambda: audio-processor
    ↓
├─ Transcribe (STT)
├─ Lambda: knowledge-retriever → S3
├─ Lambda: response-generator → Bedrock
└─ Polly (TTS)
```

### **Day 2: Add WebSocket**

```
API Gateway (WebSocket)
    ↓
Lambda: audio-stream-handler
    ↓
[Same flow as Day 1]
```

---

## Lambda Function Code Structure

### **Shared Layer** (All functions use this)

```python
# lambda_layer/rivaai_common/
├── __init__.py
├── bedrock_client.py
├── dynamodb_client.py
├── s3_client.py
└── utils.py
```

### **Function Structure**

```
lambda_functions/
├── call_handler/
│   ├── handler.py
│   └── requirements.txt
├── audio_processor/
│   ├── handler.py
│   └── requirements.txt
├── knowledge_retriever/
│   ├── handler.py
│   └── requirements.txt
├── response_generator/
│   ├── handler.py
│   └── requirements.txt
└── speech_synthesizer/
    ├── handler.py
    └── requirements.txt
```

---

## Data Flow (Complete)

### **1. Incoming Call**
```
Exotel Webhook → API Gateway → Lambda: call-handler
    ↓
Create session in DynamoDB
    ↓
Return TwiML/response to Exotel
```

### **2. Audio Processing**
```
Audio Stream → API Gateway (WebSocket) → Lambda: audio-processor
    ↓
Transcribe (STT) → Text
    ↓
Lambda: knowledge-retriever
    ↓
S3: Read knowledge documents
    ↓
Bedrock: Generate embeddings
    ↓
Vector search in DynamoDB
    ↓
Return top-K results
```

### **3. Response Generation**
```
Query + RAG Context → Lambda: response-generator
    ↓
Bedrock: Claude 3 Haiku
    ↓
Response text
    ↓
Lambda: speech-synthesizer
    ↓
Polly: TTS
    ↓
Audio chunks → API Gateway → User
```

### **4. Session Management**
```
Every interaction → Update DynamoDB session
    ↓
DynamoDB TTL (24 hours) → Auto-delete
```

---

## Cost Optimization

### **Lambda Pricing** (us-east-1)
- $0.20 per 1M requests
- $0.0000166667 per GB-second

**Estimated cost for 1000 calls:**
- 5 Lambda invocations per call = 5000 invocations
- ~2 seconds per invocation at 512MB
- Cost: ~$0.10

### **DynamoDB Pricing**
- On-demand: $1.25 per million write requests
- $0.25 per million read requests

**Estimated cost for 1000 calls:**
- 10 writes + 20 reads per call
- Cost: ~$0.02

### **S3 Pricing**
- $0.023 per GB storage
- $0.0004 per 1000 GET requests

**Estimated cost:**
- 100MB knowledge base: $0.002/month
- 5000 reads: $0.002

### **Bedrock Pricing**
- Claude 3 Haiku: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- Titan Embeddings V2: $0.0001 per 1000 tokens

**Estimated cost for 1000 calls:**
- ~$2-5 depending on response length

### **Total Estimated Cost: $5-10 for 1000 calls**

---

## Deployment Strategy (2-Day Sprint)

### **Day 1 Morning: Setup**
```bash
# Create S3 bucket
aws s3 mb s3://rivaai-knowledge-base

# Create DynamoDB tables
aws dynamodb create-table --table-name rivaai-sessions ...

# Upload knowledge base
aws s3 cp crops/ s3://rivaai-knowledge-base/crops/ --recursive
```

### **Day 1 Afternoon: Deploy Lambda Functions**
```bash
# Package and deploy each function
cd lambda_functions/call_handler
zip -r function.zip .
aws lambda create-function --function-name rivaai-call-handler ...
```

### **Day 1 Evening: Setup API Gateway**
```bash
# Create REST API
aws apigateway create-rest-api --name rivaai-api

# Create WebSocket API
aws apigatewayv2 create-api --name rivaai-ws --protocol-type WEBSOCKET
```

### **Day 2: Integration & Testing**
- Wire Lambda functions together
- Test end-to-end flow
- Fix bugs

---

## Advantages of This Architecture

✅ **Serverless** - No servers to manage
✅ **Auto-scaling** - Handles any load
✅ **Cost-effective** - Pay only for what you use
✅ **Fast deployment** - Deploy functions independently
✅ **Easy updates** - Update one function at a time
✅ **Built-in monitoring** - CloudWatch logs for everything

---

## Team Permissions Update

Update IAM policies to include:

```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:*",
    "apigateway:*",
    "dynamodb:*",
    "s3:*",
    "bedrock:*",
    "transcribe:*",
    "polly:*",
    "logs:*",
    "iam:PassRole"
  ],
  "Resource": "*"
}
```

---

## Next Steps

1. **Person 1 (You)**: Set up API Gateway + Lambda skeleton
2. **Person 2**: Create DynamoDB tables + load S3 knowledge base
3. **Person 3**: Implement Bedrock integration in Lambda
4. **Person 4**: Implement Transcribe/Polly in Lambda

This architecture is simpler, cheaper, and faster to deploy than the original ECS/RDS approach!
