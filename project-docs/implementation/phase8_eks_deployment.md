# Phase 8: EKS Deployment & Infrastructure Optimization - Implementation Plan

**Goal:** Deploy the complete RAG application to AWS EKS and validate the core value proposition: **pause/resume architecture for cost optimization**. Implement production-grade infrastructure with security, monitoring, and disaster recovery capabilities.

---

## 🏗️ Architectural Context

Phase 8 is the **Production Deployment** phase where we:
1.  **Deploy to EKS**: Apply all Terraform configurations to create production infrastructure.
2.  **Validate Pause/Resume**: Test the core cost-saving mechanism (`terraform destroy` → `terraform apply`).
3.  **Implement Cost Optimization**: S3 lifecycle policies, auto-scaling, resource tagging.
4.  **Secure Secrets**: External Secrets Operator for production secret management.
5.  **Disaster Recovery**: Backup validation and recovery procedures.

**Engineering Outcomes:**
- **Production Infrastructure**: Fully operational RAG system on EKS cluster with managed node groups.
- **Cost Optimization**: Validated "Pause/Resume" architecture with ~20-minute recovery.
- **Security Posture**: External Secrets Operator integration and IAM Least Privilege.
- **Disaster Recovery**: Tested backup and restore procedures for stateful data.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Terraform Infrastructure Deployment](#part-1-terraform-infrastructure-deployment)**
- [1.1 Backend Configuration](#11-backend-configuration)
- [1.2 VPC & Networking](#12-vpc--networking)
- [1.3 EKS Cluster](#13-eks-cluster)
- [1.4 Apply Infrastructure](#14-apply-infrastructure)

**[Part 2: Kubernetes Deployment to EKS](#part-2-kubernetes-deployment-to-eks)**
- [2.1 Configure kubectl](#21-configure-kubectl)
- [2.2 Deploy Application](#22-deploy-application)
- [2.3 Configure Ingress](#23-configure-ingress)

**[Part 3: External Secrets Operator](#part-3-external-secrets-operator)**
- [3.1 Create Secrets in AWS Secrets Manager](#31-create-secrets-in-aws-secrets-manager)
- [3.2 Install External Secrets Operator](#32-install-external-secrets-operator)
- [3.3 Configure SecretStore](#33-configure-secretstore)
- [3.4 Create ExternalSecret](#34-create-externalsecret)

**[Part 4: Cost Optimization](#part-4-cost-optimization)**
- [4.1 S3 Lifecycle Policies](#41-s3-lifecycle-policies)
- [4.2 Time-Based Auto-Scaling](#42-time-based-auto-scaling)
- [4.3 Resource Tagging](#43-resource-tagging)

**[Part 5: Pause/Resume Validation (CRITICAL)](#part-5-pauseresume-validation-critical)**
- [5.1 Pre-Destroy Checklist](#51-pre-destroy-checklist)
- [5.2 Execute Terraform Destroy](#52-execute-terraform-destroy)
- [5.3 Verify Data Persistence](#53-verify-data-persistence)
- [5.4 Execute Terraform Apply](#54-execute-terraform-apply)
- [5.5 Validate Full Recovery](#55-validate-full-recovery)

**[Part 6: Security Hardening](#part-6-security-hardening)**
- [6.1 Network Policies](#61-network-policies)
- [6.2 Pod Security Standards](#62-pod-security-standards)
- [6.3 IAM Least Privilege](#63-iam-least-privilege)

**[Part 7: Backup & Disaster Recovery](#part-7-backup--disaster-recovery)**
- [7.1 S3 Versioning](#71-s3-versioning)
- [7.2 ECR Image Backup](#72-ecr-image-backup)
- [7.3 Recovery Procedures](#73-recovery-procedures)

**[Part 7.5: Integration & Deployment Validation](#part-75-integration--deployment-validation)**

**[Part 8: Verification](#part-8-verification)**

---

## Prerequisites

- **Phase 6 Complete**: All application features operational locally.
- **AWS Account**: With appropriate permissions for EKS, VPC, S3, Secrets Manager.
- **Terraform**: v1.6+ installed.
- **kubectl**: v1.28+ installed.
- **AWS CLI**: v2+ configured with credentials.

---

## Part 1: Terraform Infrastructure Deployment

### 1.1 Backend Configuration
**File:** `terraform/backend.tf`

Configure S3 backend for Terraform state.

```hcl
terraform {
  backend "s3" {
    bucket         = "llmops-rag-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "ap-southeast-2"
    encrypt        = true
    dynamodb_table = "llmops-rag-terraform-state-lock"
  }
  
  required_version = ">= 1.6.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "LLMOps-RAG"
      Environment = var.environment
      ManagedBy   = "Terraform"
      CostCenter  = "Engineering"
    }
  }
}
```

### 1.2 VPC & Networking
**File:** `terraform/environments/prod/main.tf` (Consolidated)

```hcl
module "vpc" {
  source = "../../modules/vpc"

  project_name = "llmops-rag-pipeline"
  environment  = "prod"
  cluster_name = "llmops-rag-cluster"
}
```

### 1.3 EKS Cluster
**File:** `terraform/environments/prod/main.tf` (Consolidated)

```hcl
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "llmops-rag-cluster"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}
```



# IRSA for External Secrets Operator
module "external_secrets_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "external-secrets-${var.environment}"

  attach_external_secrets_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:external-secrets"]
    }
  }
}

# IRSA for RAG API (Bedrock, S3 access)
module "rag_api_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "rag-api-${var.environment}"

  role_policy_arns = {
    bedrock = aws_iam_policy.bedrock_access.arn
    s3      = aws_iam_policy.s3_access.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["${var.environment}:rag-api"]
    }
  }
}

# Bedrock access policy
resource "aws_iam_policy" "bedrock_access" {
  name = "rag-bedrock-access-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/amazon.nova-*",
          "arn:aws:bedrock:*::foundation-model/amazon.titan-*"
        ]
      }
    ]
  })
}

# S3 access policy
resource "aws_iam_policy" "s3_access" {
  name = "rag-s3-access-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}
```

### 1.4 Apply Infrastructure
**Commands:**

```bash
# Navigate to prod environment
cd terraform/environments/prod

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Review plan carefully
terraform show tfplan

# Apply (this will take ~20 minutes)
terraform apply tfplan

# Save outputs
terraform output -json > outputs.json
```

---

## Part 2: Kubernetes Deployment to EKS

### 2.1 Configure kubectl
**Commands:**

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --name llmops-rag-cluster \
  --region ap-southeast-2

# Verify connection
kubectl get nodes

# Create namespaces
kubectl create namespace dev
kubectl create namespace staging
kubectl create namespace prod
kubectl create namespace monitoring
kubectl create namespace mlops
```

### 2.2 Deploy Application
**File:** `scripts/deploy_to_eks.sh`

```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
NAMESPACE=$ENVIRONMENT

echo "Deploying to EKS - Environment: $ENVIRONMENT"

# Apply ConfigMaps
kubectl apply -f kubernetes/base/configmap.yaml -n $NAMESPACE

# Apply Secrets (will be replaced by External Secrets)
kubectl apply -f kubernetes/base/secrets.yaml -n $NAMESPACE

# Deploy Redis
kubectl apply -f kubernetes/base/redis-deployment.yaml -n $NAMESPACE

# Deploy Vector DB
kubectl apply -f kubernetes/base/vectordb-deployment.yaml -n $NAMESPACE

# Deploy API
kubectl apply -f kubernetes/base/deployment.yaml -n $NAMESPACE
kubectl apply -f kubernetes/base/service.yaml -n $NAMESPACE

# Deploy Monitoring
kubectl apply -f kubernetes/monitoring/ -n monitoring

# Wait for deployments
kubectl rollout status deployment/rag-api -n $NAMESPACE --timeout=5m
kubectl rollout status deployment/redis -n $NAMESPACE --timeout=5m

echo "Deployment complete!"
```

### 2.3 Configure Ingress
**File:** `kubernetes/base/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-api-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/ssl-redirect: '443'
spec:
  rules:
  - host: rag-api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rag-api-service
            port:
              number: 80
```

---

## Part 3: External Secrets Operator

### 3.1 Create Secrets in AWS Secrets Manager
**File:** `scripts/create_secrets.sh`

```bash
#!/bin/bash

# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name rag-api-secrets-prod \
  --description "Production secrets for RAG API" \
  --secret-string '{
    "OPENAI_API_KEY": "placeholder",
    "BEDROCK_GUARDRAIL_ID": "your-guardrail-id",
    "DATABASE_PASSWORD": "your-db-password"
  }' \
  --region ap-southeast-2

echo "Secret created: rag-api-secrets-prod"
```

### 3.2 Install External Secrets Operator
**Commands:**

```bash
# Add Helm repo
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

# Install ESO
helm install external-secrets \
  external-secrets/external-secrets \
  -n kube-system \
  --set installCRDs=true \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"="arn:aws:iam::ACCOUNT_ID:role/external-secrets-prod"

# Verify installation
kubectl get pods -n kube-system | grep external-secrets
```

### 3.3 Configure SecretStore
**File:** `kubernetes/base/secret-store.yaml`

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: prod
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-southeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets
```

### 3.4 Create ExternalSecret
**File:** `kubernetes/base/external-secret.yaml`

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: rag-api-secrets
  namespace: prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: rag-api-secrets
    creationPolicy: Owner
  data:
  - secretKey: OPENAI_API_KEY
    remoteRef:
      key: rag-api-secrets-prod
      property: OPENAI_API_KEY
  - secretKey: BEDROCK_GUARDRAIL_ID
    remoteRef:
      key: rag-api-secrets-prod
      property: BEDROCK_GUARDRAIL_ID
```

---

## Part 4: Cost Optimization

### 4.1 S3 Lifecycle Policies
**File:** `terraform/s3.tf`

```hcl
resource "aws_s3_bucket" "documents" {
  bucket = "llmops-rag-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Cost savings: ~50% after 30 days, ~80% after 90 days
```

### 4.2 Time-Based Auto-Scaling
**File:** `kubernetes/base/scheduled-scaler.yaml`

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-down-night
  namespace: prod
spec:
  schedule: "0 22 * * *"  # 10 PM daily
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: scaler
          containers:
          - name: kubectl
            image: bitnami/kubectl:latest
            command:
            - /bin/sh
            - -c
            - |
              kubectl scale deployment rag-api --replicas=1 -n prod
              kubectl scale deployment redis --replicas=1 -n prod
          restartPolicy: OnFailure
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: scale-up-morning
  namespace: prod
spec:
  schedule: "0 6 * * *"  # 6 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: scaler
          containers:
          - name: kubectl
            image: bitnami/kubectl:latest
            command:
            - /bin/sh
            - -c
            - |
              kubectl scale deployment rag-api --replicas=3 -n prod
              kubectl scale deployment redis --replicas=1 -n prod
          restartPolicy: OnFailure
```

### 4.3 Resource Tagging
All resources already tagged via `default_tags` in provider configuration (see 1.1).

**Verify tags:**
```bash
# Check EKS tags
aws eks describe-cluster --name llmops-rag-cluster \
  --query 'cluster.tags' --output table

# Check S3 tags
aws s3api get-bucket-tagging --bucket llmops-rag-documents-prod

# View cost allocation in AWS Cost Explorer
# Navigate to: AWS Console → Cost Explorer → Cost Allocation Tags
```

---

## Part 5: Pause/Resume Validation (CRITICAL)

### 5.0 One-Click Pause/Resume Master Script ⭐
**File:** `scripts/pause_resume.sh`

**The ultimate convenience script** - pause or resume your entire infrastructure with a single command!

```bash
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
    
    # Step 2: Destroy infrastructure
    echo -e "${GREEN}Step 2/3: Destroying infrastructure (~15 minutes)...${NC}"
    cd terraform
    terraform destroy -auto-approve
    cd ..
    
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
    cd terraform
    terraform apply -auto-approve
    cd ..
    
    # Step 2: Deploy application
    echo -e "${GREEN}Step 2/3: Deploying application to EKS (~5 minutes)...${NC}"
    aws eks update-kubeconfig --name llmops-rag-cluster --region ap-southeast-2
    ./scripts/deploy_to_eks.sh prod
    
    # Step 3: Validate recovery
    echo -e "${GREEN}Step 3/3: Validating full recovery...${NC}"
    ./scripts/validate_recovery.sh
    
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
```

**Make it executable:**
```bash
chmod +x scripts/pause_resume.sh
```

**Usage Examples:**

```bash
# Check current status
./scripts/pause_resume.sh status

# Pause infrastructure (end of day/week)
./scripts/pause_resume.sh pause

# Resume infrastructure (start of day/week)
./scripts/pause_resume.sh resume
```

**Expected Output:**
```
🛑 PAUSING INFRASTRUCTURE
This will destroy the EKS cluster but preserve all data...

Step 1/3: Running pre-destroy safety checks...
=== Pre-Destroy Checklist ===
1. Checking S3 buckets... ✓
2. Checking ECR images... ✓
3. Checking Secrets Manager... ✓
4. Documenting current state... ✓

Step 2/3: Destroying infrastructure (~15 minutes)...
[Terraform destroy output...]

Step 3/3: Verifying data persistence...
=== Verifying Data Persistence ===
1. S3 Buckets: ✓
2. ECR Repositories: ✓
3. Secrets Manager: ✓

✅ INFRASTRUCTURE PAUSED SUCCESSFULLY
Data preserved in:
  - S3 buckets (documents)
  - ECR repositories (Docker images)
  - AWS Secrets Manager (secrets)

To resume: ./scripts/pause_resume.sh resume
```

---

### 5.1 Pre-Destroy Checklist
**File:** `scripts/pre_destroy_checklist.sh`

```bash
#!/bin/bash

echo "=== Pre-Destroy Checklist ==="

# 1. Verify S3 data
echo "1. Checking S3 buckets..."
aws s3 ls s3://llmops-rag-documents-prod/ --recursive | wc -l

# 2. Verify ECR images
echo "2. Checking ECR images..."
aws ecr describe-images --repository-name llmops-rag-api \
  --query 'imageDetails[*].imageTags' --output table

# 3. Verify Secrets Manager
echo "3. Checking Secrets Manager..."
aws secretsmanager describe-secret --secret-id rag-api-secrets-prod

# 4. Document current state
echo "4. Documenting current state..."
kubectl get all -n prod > pre_destroy_state.txt
terraform output -json > pre_destroy_outputs.json

echo "=== Checklist Complete ==="
echo "Review outputs before proceeding with destroy"
```

### 5.2 Execute Terraform Destroy
**Commands:**

```bash
# CRITICAL: Run pre-destroy checklist first
./scripts/pre_destroy_checklist.sh

# Review what will be destroyed
terraform plan -destroy

# Execute destroy (takes ~15 minutes)
terraform destroy -auto-approve

# Verify all resources deleted
aws eks list-clusters --query 'clusters[?contains(@, `llmops-rag`)]'
```

### 5.3 Verify Data Persistence
**File:** `scripts/verify_persistence.sh`

```bash
#!/bin/bash

echo "=== Verifying Data Persistence ==="

# 1. S3 buckets should still exist
echo "1. S3 Buckets:"
aws s3 ls | grep llmops-rag

# 2. ECR repositories should still exist
echo "2. ECR Repositories:"
aws ecr describe-repositories --query 'repositories[*].repositoryName'

# 3. Secrets Manager secrets should still exist
echo "3. Secrets Manager:"
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `rag-api`)].Name'

# 4. Document counts
echo "4. Document count in S3:"
aws s3 ls s3://llmops-rag-documents-prod/ --recursive | wc -l

echo "=== Persistence Verified ==="
```

### 5.4 Execute Terraform Apply
**Commands:**

```bash
# Start timer
START_TIME=$(date +%s)

# Re-apply infrastructure
terraform apply -auto-approve

# Calculate recovery time
END_TIME=$(date +%s)
RECOVERY_TIME=$((END_TIME - START_TIME))
echo "Recovery time: $((RECOVERY_TIME / 60)) minutes"

# Expected: ~20 minutes
```

### 5.5 Validate Full Recovery
**File:** `scripts/validate_recovery.sh`

```bash
#!/bin/bash

echo "=== Validating Full Recovery ==="

# 1. Update kubeconfig
aws eks update-kubeconfig --name llmops-rag-cluster --region ap-southeast-2

# 2. Check cluster
kubectl get nodes

# 3. Redeploy application
./scripts/deploy_to_eks.sh prod

# 4. Wait for pods
kubectl wait --for=condition=ready pod -l app=rag-api -n prod --timeout=5m

# 5. Test health endpoint
API_URL=$(kubectl get svc rag-api-service -n prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl -f http://$API_URL/health

# 6. Test query endpoint
curl -X POST http://$API_URL/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test recovery", "domain": "general"}'

# 7. Verify data
echo "Documents in S3:"
aws s3 ls s3://llmops-rag-documents-prod/ --recursive | wc -l

echo "=== Recovery Validation Complete ==="
```

---

## Part 6: Security Hardening

### 6.1 Network Policies
**File:** `kubernetes/security/network-policy.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: rag-api-network-policy
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: rag-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: vectordb
    ports:
    - protocol: TCP
      port: 8000
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # AWS APIs
```

### 6.2 Pod Security Standards
**File:** `kubernetes/security/pod-security.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 6.3 IAM Least Privilege
Already implemented via IRSA in Part 1.3. Verify:

```bash
# Check service account annotations
kubectl get sa rag-api -n prod -o yaml

# Should show: eks.amazonaws.com/role-arn annotation
```

---

## Part 7: Backup & Disaster Recovery

### 7.1 S3 Versioning
Already enabled in Part 4.1. Verify:

```bash
aws s3api get-bucket-versioning --bucket llmops-rag-documents-prod
```

### 7.2 ECR Image Backup
**File:** `scripts/backup_ecr.sh`

```bash
#!/bin/bash

# Enable ECR image scanning
aws ecr put-image-scanning-configuration \
  --repository-name llmops-rag-api \
  --image-scanning-configuration scanOnPush=true

# Enable lifecycle policy to retain last 10 images
aws ecr put-lifecycle-policy \
  --repository-name llmops-rag-api \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }]
  }'
```

### 7.3 Recovery Procedures
**File:** `docs/disaster_recovery.md`

```markdown
# Disaster Recovery Procedures

## Scenario 1: Complete Infrastructure Loss

1. **Restore from Terraform**
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```
   Recovery Time: ~20 minutes

2. **Redeploy Application**
   ```bash
   ./scripts/deploy_to_eks.sh prod
   ```
   Recovery Time: ~5 minutes

3. **Verify Data**
   - S3 documents: Automatically available
   - ECR images: Automatically available
   - Secrets: Automatically synced via ESO

## Scenario 2: Data Corruption

1. **Restore S3 from Version**
   ```bash
   aws s3api list-object-versions --bucket llmops-rag-documents-prod
   aws s3api get-object --bucket llmops-rag-documents-prod \
     --key path/to/file --version-id VERSION_ID file.txt
   ```

## Scenario 3: Secret Compromise

1. **Rotate Secret**
   ```bash
   aws secretsmanager update-secret \
     --secret-id rag-api-secrets-prod \
     --secret-string '{...new values...}'
   ```

2. **ESO will auto-sync within 1 hour (or force refresh)**
   ```bash
   kubectl delete externalsecret rag-api-secrets -n prod
   kubectl apply -f kubernetes/base/external-secret.yaml
   ```
```

---

## Part 7.5: Integration & Deployment Validation

> **Critical**: This section validates that all deployed components (Terraform infrastructure, Kubernetes deployments, External Secrets, monitoring) work together correctly. **No additional AWS resources are created** - we're only testing what's already deployed.

### 7.5.1 Validate EKS Cluster Connectivity

**1. Verify kubectl is configured:**
```bash
# Check current context
kubectl config current-context
# Should show: arn:aws:eks:ap-southeast-2:ACCOUNT_ID:cluster/llmops-rag-cluster

# List all nodes
kubectl get nodes -o wide
# Should see 2+ nodes in Ready state
```

**2. Verify all namespaces exist:**
```bash
kubectl get namespaces
# Should see: dev, staging, prod, monitoring, mlops
```

**3. Check cluster health:**
```bash
# Check cluster addons
kubectl get daemonset -n kube-system
# Should see: aws-node, kube-proxy, ebs-csi-node

# Check system pods
kubectl get pods -n kube-system
# All pods should be Running
```

### 7.5.2 Validate Application Deployment

**1. Check all application pods are running:**
```bash
# Check prod namespace
kubectl get pods -n prod
# Should see: rag-api, redis, vectordb all Running

# Check pod logs for startup messages
kubectl logs -l app=rag-api -n prod --tail=20
# Should see: "Application startup complete"
```

**2. Verify services are created:**
```bash
kubectl get svc -n prod
# Should see: rag-api-service, redis-service, vectordb-service
```

**3. Check deployments are healthy:**
```bash
kubectl get deployments -n prod
# All deployments should show READY: X/X
```

### 7.5.3 Validate External Secrets Integration

**1. Verify External Secrets Operator is running:**
```bash
kubectl get pods -n kube-system | grep external-secrets
# Should see: external-secrets-xxxxx Running
```

**2. Check SecretStore is configured:**
```bash
kubectl get secretstore -n prod
# Should show: aws-secrets-manager
```

**3. Verify ExternalSecret is syncing:**
```bash
kubectl get externalsecret -n prod
# Should show: rag-api-secrets with READY: True

# Check the synced secret exists
kubectl get secret rag-api-secrets -n prod
# Should show the secret with DATA entries
```

**4. Validate secret values are accessible to pods:**
```bash
# Check if pod can read secrets
kubectl exec -it deployment/rag-api -n prod -- env | grep -E "BEDROCK|OPENAI"
# Should show environment variables (values will be masked)
```

### 7.5.4 Validate Service-to-Service Communication

**1. Test Redis connectivity from API pod:**
```bash
kubectl exec -it deployment/rag-api -n prod -- redis-cli -h redis-service ping
# Should return: PONG
```

**2. Test VectorDB connectivity:**
```bash
kubectl exec -it deployment/rag-api -n prod -- curl http://vectordb-service:8000/api/v2/heartbeat
# Should return heartbeat response
```

**3. Verify internal DNS resolution:**
```bash
kubectl exec -it deployment/rag-api -n prod -- nslookup redis-service
# Should resolve to cluster IP

kubectl exec -it deployment/rag-api -n prod -- nslookup vectordb-service
# Should resolve to cluster IP
```

### 7.5.5 Validate External Access via Ingress

**1. Get the Load Balancer URL:**
```bash
kubectl get ingress -n prod
# Note the ADDRESS column - this is your ALB URL
```

**2. Test external access to health endpoint:**
```bash
# Get the ALB hostname
ALB_URL=$(kubectl get ingress rag-api-ingress -n prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint (wait a few minutes for ALB to be ready)
curl http://$ALB_URL/health
# Expected: {"status":"healthy","timestamp":"..."}
```

**3. Verify SSL redirect (if configured):**
```bash
curl -I http://$ALB_URL/health
# Should see: Location: https://...
```

### 7.5.6 Validate Monitoring Integration

**1. Check Prometheus is scraping EKS pods:**
```bash
# Port forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-service 9090:9090 &

# Query targets
curl 'http://localhost:9090/api/v1/targets' | jq '.data.activeTargets[] | select(.labels.namespace=="prod")'
# Should show rag-api pods with state="up"
```

**2. Verify metrics are being collected:**
```bash
# Query a metric
curl 'http://localhost:9090/api/v1/query?query=rag_requests_total{namespace="prod"}' | jq '.data.result'
# Should show metric data
```

**3. Check Grafana dashboards:**
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/grafana-service 3000:3000 &

# Open in browser
open http://localhost:3000
# Login and verify dashboards show EKS data
```

### 7.5.7 Validate IAM Roles for Service Accounts (IRSA)

**1. Verify service account has IAM role annotation:**
```bash
kubectl get sa rag-api -n prod -o yaml | grep eks.amazonaws.com/role-arn
# Should show: eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/rag-api-prod
```

**2. Test Bedrock access from pod:**
```bash
kubectl exec -it deployment/rag-api -n prod -- python -c "
import boto3
client = boto3.client('bedrock-runtime', region_name='ap-southeast-2')
models = client.list_foundation_models()
print(f'Bedrock access: OK - Found {len(models[\"modelSummaries\"])} models')
"
# Should print: Bedrock access: OK
```

**3. Test S3 access from pod:**
```bash
kubectl exec -it deployment/rag-api -n prod -- aws s3 ls s3://llmops-rag-documents-prod/
# Should list S3 bucket contents
```

### 7.5.8 Validate Cost Optimization Features

**1. Verify S3 lifecycle policies are active:**
```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket llmops-rag-documents-prod \
  --query 'Rules[].{ID:ID,Status:Status,Transitions:Transitions}'
# Should show lifecycle rules
```

**2. Check auto-scaling CronJobs are created:**
```bash
kubectl get cronjob -n prod
# Should see: scale-down-night, scale-up-morning
```

**3. Verify resource tags for cost tracking:**
```bash
aws eks describe-cluster --name llmops-rag-cluster \
  --query 'cluster.tags' --output table
# Should show: Project, Environment, ManagedBy, CostCenter tags
```

### 7.5.9 End-to-End Integration Test

**1. Test complete RAG flow:**
```bash
# Get ALB URL
ALB_URL=$(kubectl get ingress rag-api-ingress -n prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test query endpoint
curl -X POST "http://$ALB_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the deployment process?", "domain": "engineering"}' \
  | jq '.'

# Should return:
# - answer (from LLM)
# - sources (from vector DB)
# - model_used (routing decision)
# - cached (caching status)
# - cost (cost tracking)
```

**2. Verify caching is working:**
```bash
# First query (cache miss)
time curl -X POST "http://$ALB_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test query", "domain": "general"}'
# Note the time

# Second identical query (should be cache hit)
time curl -X POST "http://$ALB_URL/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test query", "domain": "general"}'
# Should be much faster
```

**3. Check metrics were recorded:**
```bash
# Query Prometheus for the test queries
curl 'http://localhost:9090/api/v1/query?query=rag_requests_total{namespace="prod"}' | jq '.data.result[0].value[1]'
# Should show increased count
```

### 7.5.10 Pre-Production Checklist

**Before moving to verification, confirm:**

- [ ] All pods in `prod` namespace are Running
- [ ] External Secrets are syncing from AWS Secrets Manager
- [ ] Services can communicate internally (Redis, VectorDB)
- [ ] External access works via ALB/Ingress
- [ ] IRSA allows pods to access Bedrock and S3
- [ ] Monitoring is collecting metrics from EKS
- [ ] Cost optimization features are active (lifecycle, tags)
- [ ] End-to-end RAG query works successfully
- [ ] Caching is functioning correctly
- [ ] No errors in pod logs

**If any item fails, troubleshoot before proceeding to verification.**

### 7.5.11 Troubleshooting Common Issues

**Issue: Pods stuck in Pending**
```bash
# Check pod events
kubectl describe pod -l app=rag-api -n prod

# Common causes:
# - Insufficient node capacity
# - PVC not bound
# - Image pull errors
```

**Issue: External Secrets not syncing**
```bash
# Check ESO logs
kubectl logs -n kube-system -l app.kubernetes.io/name=external-secrets

# Verify IAM role permissions
aws iam get-role --role-name external-secrets-prod

# Check SecretStore status
kubectl describe secretstore aws-secrets-manager -n prod
```

**Issue: ALB not accessible**
```bash
# Check ingress status
kubectl describe ingress rag-api-ingress -n prod

# Verify ALB exists
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?contains(LoadBalancerName, `k8s-prod`)].{Name:LoadBalancerName,DNS:DNSName}'

# Check target group health
aws elbv2 describe-target-health --target-group-arn <ARN>
```

**Issue: IRSA not working**
```bash
# Verify OIDC provider exists
aws iam list-open-id-connect-providers

# Check service account annotation
kubectl get sa rag-api -n prod -o yaml

# Test from pod
kubectl exec -it deployment/rag-api -n prod -- aws sts get-caller-identity
# Should show the assumed role
```

**Issue: Monitoring not showing data**
```bash
# Check if ServiceMonitor exists
kubectl get servicemonitor -n prod

# Verify Prometheus can reach pods
kubectl exec -it -n monitoring deployment/prometheus -- wget -O- http://rag-api-service.prod.svc.cluster.local/metrics
```

---

## Part 8: Verification

### 8.1 Verification Steps

**1. Verify EKS Deployment**
```bash
# Check cluster
aws eks describe-cluster --name llmops-rag-cluster

# Check nodes
kubectl get nodes -o wide

# Check all pods
kubectl get pods --all-namespaces
```

**2. Verify Application**
```bash
# Get load balancer URL
kubectl get svc rag-api-service -n prod

# Test endpoints
curl http://<LB-URL>/health
curl -X POST http://<LB-URL>/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "domain": "general"}'
```

**3. Verify External Secrets**
```bash
# Check ESO pods
kubectl get pods -n kube-system | grep external-secrets

# Check secret sync
kubectl get externalsecret -n prod
kubectl describe externalsecret rag-api-secrets -n prod
```

**4. Verify Pause/Resume**
```bash
# Run full cycle
./scripts/pre_destroy_checklist.sh
terraform destroy -auto-approve
./scripts/verify_persistence.sh
terraform apply -auto-approve
./scripts/validate_recovery.sh
```

### 8.2 Verification Checklist

### ✅ Infrastructure
- [ ] VPC created with public/private subnets
- [ ] EKS cluster running (1.28)
- [ ] Node groups operational (2-5 nodes)
- [ ] IRSA configured for service accounts

### ✅ Application Deployment
- [ ] All pods running in prod namespace
- [ ] Load balancer provisioned
- [ ] Health checks passing
- [ ] Query endpoint functional

### ✅ External Secrets
- [ ] ESO installed and running
- [ ] SecretStore configured
- [ ] ExternalSecret syncing successfully
- [ ] Application using synced secrets

### ✅ Cost Optimization
- [ ] S3 lifecycle policies active
- [ ] Time-based scaling configured
- [ ] Resource tags visible in Cost Explorer
- [ ] Cost allocation reports working

### ✅ Pause/Resume (CRITICAL)
- [ ] Pre-destroy checklist passes
- [ ] Terraform destroy completes (~15 min)
- [ ] S3 data persists
- [ ] ECR images persist
- [ ] Secrets persist
- [ ] Terraform apply completes (~20 min)
- [ ] Application fully functional after restore
- [ ] Multiple cycles tested successfully

### ✅ Security
- [ ] Network policies enforced
- [ ] Pod security standards applied
- [ ] IAM least privilege validated
- [ ] Secrets rotation tested

### ✅ Disaster Recovery
- [ ] S3 versioning enabled
- [ ] ECR lifecycle policy configured
- [ ] Recovery procedures documented
- [ ] Recovery tested successfully

---

**Project Complete!** 🎉

You now have a production-grade RAG application on AWS EKS with:
- ✅ Validated pause/resume architecture (core value proposition)
- ✅ Cost-optimized infrastructure
- ✅ Production-grade security
- ✅ Comprehensive monitoring and observability
- ✅ MLOps capabilities (caching, routing, evaluation)
- ✅ Disaster recovery procedures

**Next Steps:** Phase 8 - Documentation & Portfolio Polish
