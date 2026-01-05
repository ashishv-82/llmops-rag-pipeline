# Phase 7: EKS Deployment & Infrastructure Optimization - Implementation Plan

**Goal:** Deploy the complete RAG application to AWS EKS and validate the core value proposition: **pause/resume architecture for cost optimization**. Implement production-grade infrastructure with security, monitoring, and disaster recovery capabilities.

---

## 🏗️ Architectural Context

Phase 7 is the **Production Deployment** phase where we:
1.  **Deploy to EKS**: Apply all Terraform configurations to create production infrastructure.
2.  **Validate Pause/Resume**: Test the core cost-saving mechanism (`terraform destroy` → `terraform apply`).
3.  **Implement Cost Optimization**: S3 lifecycle policies, auto-scaling, resource tagging.
4.  **Secure Secrets**: External Secrets Operator for production secret management.
5.  **Disaster Recovery**: Backup validation and recovery procedures.

**Engineering Outcomes:**
- Fully operational RAG system on AWS EKS.
- Validated pause/resume capability with ~20-minute recovery time.
- Cost-optimized infrastructure with lifecycle policies and auto-scaling.
- Production-grade security with External Secrets Operator.
- Documented disaster recovery procedures.

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
    dynamodb_table = "terraform-state-lock"
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
**File:** `terraform/main.tf`

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.1.2"

  name = "${var.project_name}-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["ap-southeast-2a", "ap-southeast-2b", "ap-southeast-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment == "dev" # Cost savings for dev
  enable_dns_hostnames = true
  enable_dns_support   = true

  # EKS-specific tags
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}
```

### 1.3 EKS Cluster
**File:** `terraform/eks.tf`

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Cluster endpoint configuration
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Enable IRSA (IAM Roles for Service Accounts)
  enable_irsa = true

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # Managed node groups
  eks_managed_node_groups = {
    general = {
      name = "general-${var.environment}"
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      
      min_size     = 2
      max_size     = 5
      desired_size = 2
      
      # Time-based scaling (handled by Karpenter or CronJob)
      labels = {
        role = "general"
      }
      
      tags = {
        "k8s.io/cluster-autoscaler/enabled"                = "true"
        "k8s.io/cluster-autoscaler/${var.cluster_name}"    = "owned"
      }
    }
  }

  # Cluster security group rules
  cluster_security_group_additional_rules = {
    ingress_nodes_ephemeral_ports_tcp = {
      description                = "Nodes on ephemeral ports"
      protocol                   = "tcp"
      from_port                  = 1025
      to_port                    = 65535
      type                       = "ingress"
      source_node_security_group = true
    }
  }
}

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
# Initialize Terraform
cd terraform
terraform init

# Create workspace for environment
terraform workspace new prod

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
