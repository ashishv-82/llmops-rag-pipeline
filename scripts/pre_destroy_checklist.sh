#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Pre-Destroy Safety Checks ==="

# 1. Verify S3 Documents
echo -n "1. Checking S3 Documents Bucket... "
if aws s3 ls s3://llmops-rag-documents-prod/ >/dev/null 2>&1; then
    COUNT=$(aws s3 ls s3://llmops-rag-documents-prod/documents/ --recursive | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        echo -e "${GREEN}Pass ($COUNT files found)${NC}"
    else
        echo -e "${RED}Fail (Bucket empty)${NC}"
        exit 1
    fi
else
    echo -e "${RED}Fail (Bucket not found)${NC}"
    exit 1
fi

# 2. Verify ECR Images
echo -n "2. Checking ECR Repositories... "
if aws ecr describe-repositories --repository-names llmops-rag-api >/dev/null 2>&1; then
    echo -e "${GREEN}Pass${NC}"
else
    echo -e "${RED}Fail (Repository not found)${NC}"
    exit 1
fi

# 3. Verify Secrets Manager
echo -n "3. Checking Secrets Manager... "
if aws secretsmanager describe-secret --secret-id rag-api-secrets-prod >/dev/null 2>&1; then
    echo -e "${GREEN}Pass${NC}"
else
    echo -e "${RED}Fail (Secret not found)${NC}"
    exit 1
fi

# 4. Verify EBS Volume (ChromaDB)
echo -n "4. Checking EBS Volume (ChromaDB)... "
# VOL_ID should be exported by parent script or .pause_state
if [ -z "$VOL_ID" ]; then
    if [ -f .pause_state ]; then source .pause_state; fi
fi

if [ -z "$VOL_ID" ]; then
     echo -e "${RED}Fail (VOL_ID not set)${NC}"
     exit 1
fi

if aws ec2 describe-volumes --volume-ids $VOL_ID >/dev/null 2>&1; then
    echo -e "${GREEN}Pass ($VOL_ID exists)${NC}"
else
    echo -e "${RED}Fail (Volume $VOL_ID not found)${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All safety checks passed! Safe to destroy compute resources.${NC}"
exit 0
