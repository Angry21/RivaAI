#!/bin/bash
# Deploy a Lambda function

set -e

FUNCTION_NAME=$1
FUNCTION_DIR="lambda_functions/$FUNCTION_NAME"

if [ -z "$FUNCTION_NAME" ]; then
    echo "Usage: ./deploy_lambda_function.sh <function_name>"
    echo "Example: ./deploy_lambda_function.sh call_handler"
    exit 1
fi

if [ ! -d "$FUNCTION_DIR" ]; then
    echo "Error: Function directory $FUNCTION_DIR not found"
    exit 1
fi

echo "📦 Deploying $FUNCTION_NAME..."

cd "$FUNCTION_DIR"

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -t .
fi

# Create zip
zip -r function.zip . -x "*.pyc" -x "__pycache__/*"

# Get layer ARN (you'll need to update this after deploying the layer)
LAYER_ARN=$(aws lambda list-layer-versions --layer-name rivaai-common --region us-east-1 --query 'LayerVersions[0].LayerVersionArn' --output text)

# Deploy or update function
if aws lambda get-function --function-name "rivaai-$FUNCTION_NAME" --region us-east-1 2>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name "rivaai-$FUNCTION_NAME" \
        --zip-file fileb://function.zip \
        --region us-east-1
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name "rivaai-$FUNCTION_NAME" \
        --runtime python3.11 \
        --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/rivaai-lambda-role \
        --handler handler.lambda_handler \
        --zip-file fileb://function.zip \
        --timeout 60 \
        --memory-size 512 \
        --layers "$LAYER_ARN" \
        --environment Variables="{AWS_REGION=us-east-1,SESSIONS_TABLE=rivaai-sessions}" \
        --region us-east-1
fi

echo "✅ Function rivaai-$FUNCTION_NAME deployed!"

# Clean up
rm function.zip
rm -rf boto3* botocore*

cd ../..
