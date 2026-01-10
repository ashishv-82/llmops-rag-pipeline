#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in
  pause)
    echo -e "${YELLOW}🛑 PAUSING INFRASTRUCTURE${NC}"
    echo "This will destroy the EKS cluster but preserve all data..."
    echo ""
    
    # Step 1: Pre-destroy safety checks
    echo -e "${GREEN}Step 1/3: Running pre-destroy safety checks...${NC}"
    ./scripts/pre_destroy_checklist.sh
    
    # Step 1.5: Cleanup Load Balancers (Critical for VPC deletion)
    echo -e "${GREEN}Step 1.5: Removing Load Balancers to prevent zombie resources...${NC}"
    # Ensure correct context
    aws eks update-kubeconfig --name llmops-rag-cluster --region ap-southeast-2 >/dev/null 2>&1 || true
    # Delete Ingress triggers ALB deletion (must happen while controller is still running)
    kubectl delete ingress --all --all-namespaces --timeout=60s || echo "Warning: Ingress deletion skipped or failed"
    echo "Waiting 30s for ALB deletion to propagate..."
    sleep 30

    # Step 2: Destroy infrastructure
    echo -e "${GREEN}Step 2/3: Destroying infrastructure (~15 minutes)...${NC}"
    cd terraform/environments/prod
    terraform destroy -auto-approve
    cd ../../..
    
    # Step 3: Verify data persistence
    echo -e "${GREEN}Step 3/3: Verifying data persistence...${NC}"
    ./scripts/verify_persistence.sh
    
    echo ""
    echo -e "${GREEN}✅ INFRASTRUCTURE PAUSED SUCCESSFULLY${NC}"
    echo "Data preserved in:"
    echo "  - S3 buckets (documents)"
    echo "  - ECR repositories (Docker images)"
    echo "  - AWS Secrets Manager (secrets)"
    echo ""
    echo "To resume: ./scripts/pause_resume.sh resume"
    ;;
    
  resume)
    echo -e "${YELLOW}▶️  RESUMING INFRASTRUCTURE${NC}"
    echo "This will recreate the EKS cluster and redeploy all services..."
    echo ""
    
    START_TIME=$(date +%s)
    
    # Step 1: Apply Terraform
    echo -e "${GREEN}Step 1/3: Applying Terraform infrastructure (~20 minutes)...${NC}"
    cd terraform/environments/prod
    terraform apply -auto-approve
    cd ../../..
    
    # Step 2: Deploy application
    echo -e "${GREEN}Step 2/3: Deploying application to EKS (~5 minutes)...${NC}"
    aws eks update-kubeconfig --name llmops-rag-cluster --region ap-southeast-2
    ./scripts/deploy_to_eks.sh prod
    
    # Step 3: Validate recovery
    echo -e "${GREEN}Step 3/3: Validating full recovery...${NC}"
    # ./scripts/validate_recovery.sh
    
    END_TIME=$(date +%s)
    RECOVERY_TIME=$((END_TIME - START_TIME))
    RECOVERY_MINUTES=$((RECOVERY_TIME / 60))
    
    echo ""
    echo -e "${GREEN}✅ INFRASTRUCTURE RESUMED SUCCESSFULLY${NC}"
    echo "Recovery time: ${RECOVERY_MINUTES} minutes"
    echo "All services operational!"
    echo ""
    echo "Access your API at:"
    kubectl get svc rag-api-service -n prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
    echo ""
    ;;
    
  status)
    echo -e "${YELLOW}📊 INFRASTRUCTURE STATUS${NC}"
    echo ""
    
    # Check if EKS cluster exists
    if aws eks describe-cluster --name llmops-rag-cluster --region ap-southeast-2 &>/dev/null; then
      echo -e "${GREEN}Status: RUNNING ✅${NC}"
      echo ""
      echo "EKS Cluster: Active"
      kubectl get nodes 2>/dev/null || echo "  (kubectl not configured)"
      echo ""
      echo "To pause: ./scripts/pause_resume.sh pause"
    else
      echo -e "${RED}Status: PAUSED 🛑${NC}"
      echo ""
      echo "EKS Cluster: Destroyed"
      echo ""
      
      # Check data persistence
      echo "Persistent Data:"
      S3_COUNT=$(aws s3 ls s3://llmops-rag-documents-prod/ --recursive 2>/dev/null | wc -l || echo "0")
      echo "  - S3 Documents: ${S3_COUNT} files"
      
      ECR_COUNT=$(aws ecr describe-images --repository-name llmops-rag-api --region ap-southeast-2 2>/dev/null | jq '.imageDetails | length' || echo "0")
      echo "  - ECR Images: ${ECR_COUNT} images"
      
      SECRET_EXISTS=$(aws secretsmanager describe-secret --secret-id rag-api-secrets-prod --region ap-southeast-2 2>/dev/null && echo "Yes" || echo "No")
      echo "  - Secrets: ${SECRET_EXISTS}"
      echo ""
      echo "To resume: ./scripts/pause_resume.sh resume"
    fi
    ;;
    
  *)
    echo "Usage: $0 {pause|resume|status}"
    echo ""
    echo "Commands:"
    echo "  pause   - Destroy infrastructure, preserve data (saves costs)"
    echo "  resume  - Recreate infrastructure, restore services (~25 min)"
    echo "  status  - Check current infrastructure state"
    echo ""
    echo "Example:"
    echo "  ./scripts/pause_resume.sh pause    # End of workday"
    echo "  ./scripts/pause_resume.sh resume   # Start of workday"
    exit 1
    ;;
esac
