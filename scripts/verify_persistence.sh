#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Data Persistence Verification ==="

ERROR=0

# 1. Verify S3 Documents
echo -n "1. Checking S3 Documents are still there... "
COUNT=$(aws s3 ls s3://llmops-rag-documents-prod/documents/ --recursive 2>/dev/null | wc -l || echo 0)
if [ "$COUNT" -gt 0 ]; then
    echo -e "${GREEN}Pass ($COUNT files)${NC}"
else
    echo -e "${RED}FAIL (Files missing)${NC}"
    ERROR=1
fi

# 2. Verify ECR Images
echo -n "2. Checking ECR Images still exist... "
API_IMG=$(aws ecr describe-images --repository-name llmops-rag-api 2>/dev/null | grep imageDigest | wc -l || echo 0)
FRONT_IMG=$(aws ecr describe-images --repository-name llmops-rag-frontend 2>/dev/null | grep imageDigest | wc -l || echo 0)

if [ "$API_IMG" -gt 0 ] && [ "$FRONT_IMG" -gt 0 ]; then
    echo -e "${GREEN}Pass (API: $API_IMG, Frontend: $FRONT_IMG)${NC}"
else
    echo -e "${RED}FAIL (Images missing)${NC}"
    ERROR=1
fi

# 3. Verify Secrets
echo -n "3. Checking Secrets Manager... "
if aws secretsmanager describe-secret --secret-id rag-api-secrets-prod >/dev/null 2>&1; then
    echo -e "${GREEN}Pass${NC}"
else
    echo -e "${RED}FAIL (Secret missing)${NC}"
    ERROR=1
fi

# 4. Verify EBS Volume
echo -n "4. Checking EBS Volume exists... "
# Load state if not set
if [ -z "$VOL_ID" ]; then
    if [ -f .pause_state ]; then source .pause_state; fi
fi

if [ -z "$VOL_ID" ]; then
    echo -e "${RED}FAIL (VOL_ID unknown)${NC}"
    ERROR=1
else
    STATE=$(aws ec2 describe-volumes --volume-ids $VOL_ID --query 'Volumes[0].State' --output text 2>/dev/null)
    if [ "$STATE" == "available" ] || [ "$STATE" == "in-use" ]; then
        echo -e "${GREEN}Pass (Volume $VOL_ID is $STATE)${NC}"
    else
        echo -e "${RED}FAIL (Volume missing or error)${NC}"
        ERROR=1
    fi
fi

if [ $ERROR -eq 1 ]; then
    echo -e "${RED}CRITICAL: SOME DATA WAS LOST OR IS INACCESSIBLE${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ Data Persistence Verified. Infrastructure is paused but data is safe.${NC}"
    exit 0
fi
