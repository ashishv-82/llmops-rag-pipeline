#!/bin/bash
# Bootstrap script for Terraform backend resources
# Creates S3 bucket and DynamoDB table for Terraform state management

set -e  # Exit on any error

# Configuration
REGION="ap-southeast-2"
S3_BUCKET="llmops-rag-terraform-state"
DYNAMODB_TABLE="llmops-rag-terraform-state-lock"

echo "========================================="
echo "Terraform Backend Bootstrap"
echo "========================================="
echo ""
echo "This script will create:"
echo "  - S3 bucket: ${S3_BUCKET}"
echo "  - DynamoDB table: ${DYNAMODB_TABLE}"
echo "  - Region: ${REGION}"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Creating S3 bucket for Terraform state..."
echo "=================================================="

# Create S3 bucket
if aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${S3_BUCKET}" --region "${REGION}"
    echo "✅ S3 bucket created: ${S3_BUCKET}"
else
    echo "⚠️  S3 bucket already exists: ${S3_BUCKET}"
fi

# Enable versioning
echo "Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "${S3_BUCKET}" \
  --versioning-configuration Status=Enabled \
  --region "${REGION}"
echo "✅ Versioning enabled"

# Enable encryption
echo "Enabling encryption..."
aws s3api put-bucket-encryption \
  --bucket "${S3_BUCKET}" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }' \
  --region "${REGION}"
echo "✅ Encryption enabled"

# Block public access
echo "Blocking public access..."
aws s3api put-public-access-block \
  --bucket "${S3_BUCKET}" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
  --region "${REGION}"
echo "✅ Public access blocked"

echo ""
echo "Step 2: Creating DynamoDB table for state locking..."
echo "====================================================="

# Check if table exists
if aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" 2>&1 | grep -q 'ResourceNotFoundException'; then
    aws dynamodb create-table \
      --table-name "${DYNAMODB_TABLE}" \
      --attribute-definitions AttributeName=LockID,AttributeType=S \
      --key-schema AttributeName=LockID,KeyType=HASH \
      --billing-mode PAY_PER_REQUEST \
      --region "${REGION}" \
      --tags Key=Project,Value=LLMOps Key=Purpose,Value=TerraformStateLock \
      > /dev/null
    echo "✅ DynamoDB table created: ${DYNAMODB_TABLE}"
    
    echo "Waiting for table to become active..."
    aws dynamodb wait table-exists \
      --table-name "${DYNAMODB_TABLE}" \
      --region "${REGION}"
    echo "✅ DynamoDB table is active"
else
    echo "⚠️  DynamoDB table already exists: ${DYNAMODB_TABLE}"
fi

echo ""
echo "Step 3: Verifying resources..."
echo "==============================="

# Verify S3 bucket
echo -n "S3 bucket: "
if aws s3 ls "s3://${S3_BUCKET}" --region "${REGION}" > /dev/null 2>&1; then
    echo "✅ ${S3_BUCKET}"
else
    echo "❌ ${S3_BUCKET} - NOT FOUND"
    exit 1
fi

# Verify versioning
echo -n "Versioning: "
VERSIONING=$(aws s3api get-bucket-versioning --bucket "${S3_BUCKET}" --region "${REGION}" --query 'Status' --output text)
if [ "${VERSIONING}" = "Enabled" ]; then
    echo "✅ Enabled"
else
    echo "❌ Not enabled"
    exit 1
fi

# Verify DynamoDB table
echo -n "DynamoDB table: "
TABLE_STATUS=$(aws dynamodb describe-table --table-name "${DYNAMODB_TABLE}" --region "${REGION}" --query 'Table.TableStatus' --output text)
if [ "${TABLE_STATUS}" = "ACTIVE" ]; then
    echo "✅ ${DYNAMODB_TABLE} (${TABLE_STATUS})"
else
    echo "❌ ${DYNAMODB_TABLE} (${TABLE_STATUS})"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ Bootstrap Complete!"
echo "========================================="
echo ""
echo "Backend resources are ready:"
echo "  - S3 bucket: ${S3_BUCKET}"
echo "  - DynamoDB table: ${DYNAMODB_TABLE}"
echo ""
echo "You can now run:"
echo "  cd terraform/environments/dev"
echo "  terraform init"
echo "  terraform apply"
echo ""
