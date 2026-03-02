#!/bin/bash
# Set up AWS infrastructure for RivaAI

set -e

echo "🚀 Setting up AWS infrastructure for RivaAI..."

AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Account ID: $ACCOUNT_ID"
echo "Region: $AWS_REGION"

# Step 1: Create IAM role for Lambda
echo ""
echo "📋 Step 1: Creating IAM role for Lambda..."

ROLE_NAME="rivaai-lambda-role"

# Check if role exists
if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "Role $ROLE_NAME already exists"
else
    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json

    # Attach policies
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonTranscribeFullAccess

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonPollyFullAccess

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

    echo "✅ Role created and policies attached"
    echo "⏳ Waiting 10 seconds for role to propagate..."
    sleep 10
fi

# Step 2: Create DynamoDB table for sessions
echo ""
echo "📊 Step 2: Creating DynamoDB tables..."

TABLE_NAME="rivaai-sessions"

if aws dynamodb describe-table --table-name $TABLE_NAME --region $AWS_REGION 2>/dev/null; then
    echo "Table $TABLE_NAME already exists"
else
    aws dynamodb create-table \
        --table-name $TABLE_NAME \
        --attribute-definitions \
            AttributeName=session_id,AttributeType=S \
        --key-schema \
            AttributeName=session_id,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region $AWS_REGION \
        --tags Key=Project,Value=RivaAI

    # Enable TTL
    aws dynamodb update-time-to-live \
        --table-name $TABLE_NAME \
        --time-to-live-specification "Enabled=true, AttributeName=ttl" \
        --region $AWS_REGION

    echo "✅ Table $TABLE_NAME created with TTL enabled"
fi

# Step 3: Create S3 bucket for knowledge base
echo ""
echo "🪣 Step 3: Creating S3 bucket..."

BUCKET_NAME="rivaai-knowledge-base-$ACCOUNT_ID"

if aws s3 ls "s3://$BUCKET_NAME" 2>/dev/null; then
    echo "Bucket $BUCKET_NAME already exists"
else
    aws s3 mb "s3://$BUCKET_NAME" --region $AWS_REGION
    echo "✅ Bucket $BUCKET_NAME created"
fi

# Step 4: Create API Gateway
echo ""
echo "🌐 Step 4: Creating API Gateway..."

API_NAME="rivaai-api"

# Check if API exists
API_ID=$(aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='$API_NAME'].id" --output text)

if [ -z "$API_ID" ]; then
    API_ID=$(aws apigateway create-rest-api \
        --name $API_NAME \
        --description "RivaAI REST API" \
        --region $AWS_REGION \
        --query 'id' \
        --output text)
    echo "✅ API Gateway created: $API_ID"
else
    echo "API Gateway already exists: $API_ID"
fi

echo ""
echo "✅ AWS infrastructure setup complete!"
echo ""
echo "Summary:"
echo "  - IAM Role: $ROLE_NAME"
echo "  - DynamoDB Table: $TABLE_NAME"
echo "  - S3 Bucket: $BUCKET_NAME"
echo "  - API Gateway: $API_ID"
echo ""
echo "Next steps:"
echo "  1. Deploy Lambda layer: ./scripts/deploy_lambda_layer.sh"
echo "  2. Deploy Lambda functions: ./scripts/deploy_lambda_function.sh call_handler"
echo "  3. Configure API Gateway endpoints"
