# AWS Deployment Guide for RivaAI

This guide walks you through deploying RivaAI to AWS infrastructure.

## Prerequisites

- AWS Account with credits activated
- AWS CLI installed and configured (`aws configure`)
- Docker installed locally
- Python 3.11+ installed

## Architecture Overview

```
User Phone Call
    ↓
Twilio (PSTN Gateway)
    ↓
ALB (Application Load Balancer) - WebSocket support
    ↓
ECS Fargate (FastAPI app)
    ↓
├─→ RDS PostgreSQL (pgvector) - Knowledge Base
├─→ ElastiCache Redis - Session Store
├─→ Bedrock - LLM (Claude 3 Haiku/Sonnet)
├─→ Deepgram API - STT (external)
└─→ ElevenLabs API - TTS (external)
```

## Step-by-Step Deployment

##