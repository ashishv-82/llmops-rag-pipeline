#!/bin/bash
set -e

# Configuration
REGION="ap-southeast-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="llmops-rag-api"
IMAGE_TAG=${1:-latest}  # Accept tag as argument, default to latest
ECR_URL="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}"

echo "🚀 Starting API Build & Push..."
echo "----------------------------------------"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Repository: $REPO_NAME"
echo "Tag: $IMAGE_TAG"
echo "Target: $FULL_IMAGE_NAME"
echo "----------------------------------------"

# 1. Login to ECR
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URL

# 2. Check if repo exists
if ! aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION >/dev/null 2>&1; then
    echo "❌ Repository $REPO_NAME does not exist!"
    exit 1
fi

# 3. Build Docker Image
echo "📦 Building Docker image..."
docker build --platform linux/amd64 -t $REPO_NAME -f api/Dockerfile .

# 4. Tag Image
echo "🏷️  Tagging image..."
docker tag $REPO_NAME:latest $FULL_IMAGE_NAME

# 5. Push Image
echo "⬆️  Pushing to ECR..."
docker push $FULL_IMAGE_NAME

echo "----------------------------------------"
echo "✅ API Image Pushed Successfully!"
echo "   Image: $FULL_IMAGE_NAME"
echo "----------------------------------------"
