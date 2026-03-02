# RivaAI 24-Hour Deployment Guide

This guide walks you through deploying RivaAI to AWS and achieving your first working phone call within 24 hours of receiving AWS credits.

## Prerequisites

Before starting, ensure you have:

- [ ] AWS account with credits activated
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Docker installed
- [ ] Terraform installed (>= 1.0)
- [ ] Python 3.11+ installed
- [ ] Git repository cloned
- [ ] Twilio account with phone number
- [ ] API keys ready:
  - Twilio Account SID and Auth Token
  - Deepgram API key
  - ElevenLabs API key
  - OpenAI API key (for initial deployment)

## Hour 0-4: Infrastructure Setup

### Step 1: Set Environment Variables

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export ENVIRONMENT=dev

# Twilio Configuration
export TWILIO_ACCOUNT_SID=your_account_sid
export TWILIO_AUTH_TOKEN=your_auth_token
export TWILIO_PHONE_NUMBER=+1234567890

# Speech Services
export DEEPGRAM_API_KEY=your_deepgram_key
export ELEVENLABS_API_KEY=your_elevenlabs_key

# LLM Services (temporary, will migrate to Bedrock)
export OPENAI_API_KEY=your_openai_key

# Deployment URL (will be set after deployment)
export RIVAAI_BASE_URL=http://your-alb-dns-name
```

### Step 2: Build and Deploy

```bash
# Make deployment script executable
chmod +x scripts/deploy_to_aws.sh

# Run deployment (this will take 15-20 minutes)
./scripts/deploy_to_aws.sh
```

This script will:
1. Build Docker image
2. Push to Amazon ECR
3. Deploy infrastructure with Terraform (VPC, RDS, Redis, ECS, ALB)
4. Initialize PostgreSQL with pgvector
5. Load initial knowledge base (Wheat domain)

### Step 3: Verify Infrastructure

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster rivaai-dev \
  --services rivaai-dev-service \
  --region us-east-1

# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier rivaai-dev-db \
  --region us-east-1

# Check application logs
aws logs tail /ecs/rivaai-dev --follow --region us-east-1
```

## Hour 4-8: Bedrock Integration

### Step 4: Migrate to Bedrock

```bash
# Run Bedrock migration script
python scripts/bedrock_migration.py
```

This will:
1. Regenerate embeddings using Titan Embeddings V2
2. Update knowledge base with new embeddings
3. Configure Bedrock model settings

### Step 5: Update Application Configuration

Add to your `.env` or update Secrets Manager:

```bash
# Update secrets in AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id rivaai-dev-secrets \
  --secret-string '{
    "AWS_REGION": "us-east-1",
    "BEDROCK_MAIN_MODEL": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "BEDROCK_FAST_MODEL": "anthropic.claude-3-haiku-20240307-v1:0",
    "BEDROCK_EMBEDDING_MODEL": "amazon.titan-embed-text-v2:0"
  }' \
  --region us-east-1

# Restart ECS service to pick up new configuration
aws ecs update-service \
  --cluster rivaai-dev \
  --service rivaai-dev-service \
  --force-new-deployment \
  --region us-east-1
```

## Hour 8-16: End-to-End Testing

### Step 6: Configure Twilio Webhook

Get your ALB DNS name:

```bash
cd infrastructure/terraform
terraform output alb_dns_name
```

Configure Twilio:
1. Go to Twilio Console → Phone Numbers
2. Select your phone number
3. Under "Voice & Fax", set:
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://your-alb-dns/webhooks/twilio/voice`
   - **HTTP**: POST
4. Save

### Step 7: Run Deployment Tests

```bash
# Set base URL from Terraform output
export RIVAAI_BASE_URL=http://$(cd infrastructure/terraform && terraform output -raw alb_dns_name)

# Run test suite
python scripts/test_deployment.py
```

Expected output:
```
✓ Health check passed
✓ Database connection healthy
✓ Redis connection healthy
✓ Knowledge base retrieval successful
✓ TTS synthesis successful
✓ Twilio webhook configured correctly
✓ WebSocket endpoint exists

Results: 7/7 tests passed
🎉 All tests passed! System is ready for phone calls.
```

### Step 8: Make Your First Test Call

1. **Call your Twilio number** from any phone
2. **Wait for greeting** (should hear within 3 seconds)
3. **Speak in Hindi**: "गेहूं की खेती के बारे में बताओ" (Tell me about wheat farming)
4. **Listen for response** (should start within 3 seconds)

Expected flow:
- System answers: "नमस्ते, मैं आपकी कैसे मदद कर सकता हूं?" (Hello, how can I help you?)
- You speak about wheat farming
- System retrieves information from knowledge base
- System responds with relevant farming advice

### Step 9: Monitor and Debug

```bash
# Watch application logs in real-time
aws logs tail /ecs/rivaai-dev --follow --region us-east-1

# Check for errors
aws logs filter-pattern /ecs/rivaai-dev --filter-pattern "ERROR" --region us-east-1

# Check latency metrics
aws logs filter-pattern /ecs/rivaai-dev --filter-pattern "latency" --region us-east-1
```

## Hour 16-24: Validation & Optimization

### Step 10: Validate Latency Requirements

Test each component:

```bash
# Test call establishment (<3s)
# Test STT partial transcript (<500ms)
# Test knowledge retrieval (<500ms)
# Test TTS first chunk (<800ms)
```

Monitor CloudWatch metrics:
- Go to CloudWatch → Metrics → Custom Namespaces → RivaAI
- Check latency percentiles (p50, p95, p99)

### Step 11: Test Multi-Language Support

Make test calls in different languages:

1. **Hindi**: "गेहूं की खेती के बारे में बताओ"
2. **Marathi**: "गहूच्या शेतीबद्दल सांगा"
3. **Telugu**: "గోధుమ వ్యవసాయం గురించి చెప్పండి"

### Step 12: Document Issues and Next Steps

Create a checklist:

**Working:**
- [ ] Call establishment
- [ ] Audio routing
- [ ] STT transcription (Hindi)
- [ ] Knowledge retrieval
- [ ] TTS synthesis
- [ ] End-to-end latency

**Not Yet Implemented:**
- [ ] Barge-in handling
- [ ] Circuit breaker (safety)
- [ ] Session resumption
- [ ] PII masking
- [ ] Full knowledge base (only Wheat domain loaded)

## Success Criteria

By hour 24, you should have:

✅ Working phone number that answers calls
✅ Speech-to-text transcription in Hindi
✅ Knowledge base retrieval for Wheat farming
✅ Text-to-speech response in Hindi
✅ End-to-end latency <3 seconds for simple queries
✅ All deployment tests passing

## Troubleshooting

### Issue: Health check failing

```bash
# Check ECS task status
aws ecs list-tasks --cluster rivaai-dev --region us-east-1

# Check task logs
aws logs tail /ecs/rivaai-dev --follow --region us-east-1
```

### Issue: Database connection error

```bash
# Verify RDS is running
aws rds describe-db-instances --db-instance-identifier rivaai-dev-db --region us-east-1

# Check security group rules
aws ec2 describe-security-groups --filters "Name=group-name,Values=rivaai-dev-rds-sg" --region us-east-1
```

### Issue: No audio on call

```bash
# Check Twilio webhook logs
# Go to Twilio Console → Monitor → Logs → Errors

# Verify WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://your-alb-dns/ws/media
```

### Issue: Knowledge base returns no results

```bash
# Verify embeddings were generated
psql -h your-db-endpoint -U rivaai_admin -d rivaai \
  -c "SELECT COUNT(*) FROM knowledge_items WHERE embedding IS NOT NULL;"

# Re-run knowledge base loader
python scripts/load_knowledge_base.py
```

## Next Steps After 24 Hours

Once basic flow is working:

1. **Implement safety mechanisms** (Circuit breaker - CRITICAL)
2. **Add barge-in handling** for natural interruptions
3. **Expand knowledge base** beyond Wheat domain
4. **Implement session management** with Redis
5. **Add PII masking** for privacy
6. **Load test** with multiple concurrent calls
7. **Optimize latency** for complex queries

## Cost Monitoring

Monitor AWS costs:

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-03-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --region us-east-1
```

Expected costs (dev environment):
- RDS db.t3.medium: ~$50/month
- ElastiCache cache.t3.micro: ~$12/month
- ECS Fargate (2 tasks): ~$30/month
- ALB: ~$20/month
- Data transfer: Variable
- **Total**: ~$112/month + API costs (Deepgram, ElevenLabs, Bedrock)

## Support

If you encounter issues:

1. Check application logs: `aws logs tail /ecs/rivaai-dev --follow`
2. Review Twilio webhook logs in Twilio Console
3. Check CloudWatch metrics for latency spikes
4. Verify all environment variables are set correctly

## Conclusion

By following this guide, you should have a working RivaAI deployment on AWS within 24 hours, capable of handling phone calls with voice interaction in Hindi, retrieving farming knowledge, and responding with natural speech.

The foundation is now in place to build out the remaining features: safety mechanisms, barge-in handling, expanded knowledge base, and production-grade reliability.
