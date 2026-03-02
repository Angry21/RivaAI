#!/bin/bash
# Deploy Lambda layer with shared dependencies

set -e

echo "📦 Building Lambda layer..."

cd lambda_functions/shared_layer

# Create zip
zip -r layer.zip python/

# Upload to AWS
aws lambda publish-layer-version \
    --layer-name rivaai-common \
    --description "Shared utilities for RivaAI Lambda functions" \
    --zip-file fileb://layer.zip \
    --compatible-runtimes python3.11 \
    --region us-east-1

echo "✅ Lambda layer deployed!"

# Clean up
rm layer.zip

cd ../..
