# Phase 2: Kubernetes Orchestration - Implementation Plan

**Goal:** Transition from local Docker execution to container orchestration. We will validate the application on a local Kubernetes cluster (Minikube) before defining the production-grade AWS EKS infrastructure in Terraform.

---

## 🏗️ Architectural Context

Phase 2 executes the **"Verify First"** methodology:
1.  **Local Orchestration**: Validate manifests and networking locally (Minikube).
2.  **Infrastructure Definition**: Write the Terraform code for EKS (without incurring costs yet).
3.  **Future Execution**: We will apply the EKS Terraform in Phase 7, once the application logic is mature.

**Engineering Outcomes:**
- Container orchestration mastery (Pods, Services, Deployments).
- "Config-as-Code" via ConfigMaps and Secrets.
- Production-ready Terraform modules for VPC and EKS.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Local Cluster Orchestration](#part-1-local-cluster-orchestration)**
- [1.1 Start Minikube & Configure Context](#11-start-minikube--configure-context)
- [1.2 Create Namespaces](#12-create-namespaces)

**[Part 2: Kubernetes Manifests](#part-2-kubernetes-manifests)**
- [2.1 Create Base Directory Structure](#21-create-base-directory-structure)
- [2.2 Define ConfigMap & Secrets](#22-define-configmap--secrets)
- [2.3 Define Deployment Strategy](#23-define-deployment-strategy)
- [2.4 Define Service Networking](#24-define-service-networking)

**[Part 3: Local Deployment & Validation](#part-3-local-deployment--validation)**
- [3.1 Deploy to Local Cluster](#31-deploy-to-local-cluster)
- [3.2 Verify Pod Health & Probes](#32-verify-pod-health--probes)
- [3.3 Test Service Endpoints](#33-test-service-endpoints)

**[Part 4: EKS Infrastructure Preparation (Terraform)](#part-4-eks-infrastructure-preparation-terraform)**
- [4.1 Create VPC Module](#41-create-vpc-module)
- [4.2 Create EKS Module](#42-create-eks-module)
- [4.3 Create IAM Roles for Service Accounts (IRSA)](#43-create-iam-roles-for-service-accounts-irsa)

**[Part 5: Verification](#part-5-verification)**
- [5.1 Manual Verification Steps](#51-manual-verification-steps)
- [5.2 Verification Checklist](#52-verification-checklist)

---

## Prerequisites

- **Phase 1 Complete**: Docker image `llmops-rag-api:latest` built locally.
- **Tools Installed**: `minikube`, `kubectl`, `terraform`.
- **Environment**: Virtual environment active (`source .venv/bin/activate`).

---

## Part 1: Local Cluster Orchestration

### 1.1 Start Minikube & Configure Context
Ensure your local simulation environment is matching the production behavior.

```bash
# Start Minikube (if not running)
minikube start --driver=docker

# Verify Context
kubectl config current-context
# Should output: minikube
```

### 1.2 Create Namespaces
We use namespaces to isolate environments (Dev vs. Prod) even locally.

```bash
# Create dev namespace
kubectl create namespace dev

# Set context to use this namespace by default
kubectl config set-context --current --namespace=dev
```

---

## Part 2: Kubernetes Manifests

We will write **declarative YAML** files. This is the source of truth for our application state.

### 2.1 Create Base Directory Structure
```bash
mkdir -p kubernetes/base
mkdir -p kubernetes/overlays/{dev,prod}
```

### 2.2 Define ConfigMap & Secrets

**File:** `kubernetes/base/configmap.yaml`
_Purpose: Non-sensitive configuration decoupled from code._

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-api-config
data:
  APP_ENV: "dev"
  AWS_REGION: "ap-southeast-2"
  DOCUMENTS_BUCKET: "llmops-rag-documents-dev"
  # DB Hosts will go here later
```

**File:** `kubernetes/base/secrets.yaml`
_Purpose: Sensitive credentials (placeholder for local dev)._

> [!CAUTION]
> **NEVER commit real credentials to Git.**
> 1. Run `echo "kubernetes/base/secrets.yaml" >> .gitignore` immediately.
> 2. The value below is just base64 for "placeholder".

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-api-secrets
type: Opaque
data:
  # Base64 encoded values (echo -n "your-key" | base64)
  # Example below decodes to: "placeholder"
  OPENAI_API_KEY: "cGxhY2Vob2xkZXIK" 
```

### 2.3 Define Deployment Strategy

**File:** `kubernetes/base/deployment.yaml`
_Purpose: Defines how the application runs (replicas, health checks, resources)._

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-api
  labels:
    app: rag-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag-api
  template:
    metadata:
      labels:
        app: rag-api
    spec:
      containers:
      - name: api
        image: llmops-rag-api:latest
        imagePullPolicy: Never # Use local docker image
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: rag-api-config
        - secretRef:
            name: rag-api-secrets
        # Critical for Zero-Downtime Deployments
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 2.4 Define Service Networking

**File:** `kubernetes/base/service.yaml`
_Purpose: Stable network endpoint for the pods._

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-api-service
spec:
  selector:
    app: rag-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP
```

---

## Part 3: Local Deployment & Validation

### 3.1 Deploy to Local Cluster

Load the local docker image into Minikube so it doesn't try to pull from Docker Hub.

```bash
# Point minikube to local docker env (Run in your terminal)
eval $(minikube docker-env)

# Rebuild image strictly into Minikube's docker daemon
docker build -t llmops-rag-api:latest -f api/Dockerfile .

# Apply manifests
kubectl apply -f kubernetes/base/
```

### 3.2 Verify Pod Health & Probes

```bash
# Check if pods are running
kubectl get pods -n dev
# Should see STATUS: Running

# Check pod logs
kubectl logs -l app=rag-api -n dev

# Check if the deployment is ready
kubectl get deployment rag-api -n dev

# Check events (useful if ImagePullBackOff occurs)
kubectl describe pod -l app=rag-api
```

### 3.3 Test Service Endpoints

Since `ClusterIP` needs a proxy to be reached from your Mac:

**Step 1: Set up port forwarding (in a separate terminal)**
```bash
# IMPORTANT: Specify the namespace where your service is running
kubectl port-forward service/rag-api-service 8080:80 -n dev

# You should see:
# Forwarding from 127.0.0.1:8080 -> 8000
# Forwarding from [::1]:8080 -> 8000
```

**Step 2: Test all health endpoints (in your main terminal)**
```bash
# Test basic health check
curl http://localhost:8080/health
# Expected: {"status":"healthy","timestamp":"2026-01-05T10:59:32.296231"}

# Test readiness probe (used by Kubernetes)
curl http://localhost:8080/health/ready
# Expected: {"status":"ready","checks":{"api":"ok"}}

# Test liveness probe (used by Kubernetes)
curl http://localhost:8080/health/live
# Expected: {"status":"alive"}

# Test root endpoint
curl http://localhost:8080/
# Expected: {"message":"Welcome to LLMOps RAG Pipeline","version":"0.1.0","docs":"/docs"}
```

**Step 3: Verify environment variables are injected**
```bash
# Check if ConfigMap and Secrets are mounted correctly
kubectl exec -n dev -it $(kubectl get pod -n dev -l app=rag-api -o jsonpath='{.items[0].metadata.name}') -- env | grep -E 'APP_ENV|AWS_REGION|DOCUMENTS_BUCKET'

# Expected output:
# APP_ENV=dev
# AWS_REGION=ap-southeast-2
# DOCUMENTS_BUCKET=llmops-rag-documents-dev
```

**Step 4: Check resource usage**
```bash
# View resource consumption
kubectl top pod -n dev -l app=rag-api

# Expected output similar to:
# NAME                       CPU(cores)   MEMORY(bytes)
# rag-api-868d5ff998-qp6m5   1m           45Mi
```

**Troubleshooting Tips:**
- If `curl` returns nothing, ensure port-forward is running with `-n dev` flag
- If you see "connection refused", check that the pod is in `Running` status
- If health checks fail, check pod logs: `kubectl logs -n dev -l app=rag-api`
- If you see "secret not found" warnings in events, ensure `secrets.yaml` was applied successfully

---

## Part 4: EKS Infrastructure Preparation (Terraform)

**Architectural Note:** We are defining these modules now to ensure our K8s manifests align with the future cloud infrastructure. We will **NOT apply** them yet to save costs.

### 4.1 Create VPC Module
**File:** `terraform/modules/vpc/main.tf`
_Purpose: Isolated network for our cluster._

```hcl
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "${var.project_name}-vpc-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["ap-southeast-2a", "ap-southeast-2b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true # Save costs in Dev
  enable_dns_hostnames = true

  tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}
```

### 4.2 Create EKS Module
**File:** `terraform/modules/eks/main.tf`
_Purpose: The managed Kubernetes control plane._

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  # Security: Private endpoint + Public access (restricted usage)
  cluster_endpoint_public_access = true

  # OIDC for Service Accounts (Critical for Pods -> AWS Permissions)
  enable_irsa = true

  eks_managed_node_groups = {
    initial = {
      min_size     = 1
      max_size     = 2
      desired_size = 1

      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }
  }
}
```

### 4.3 Create IAM Roles for Service Accounts (IRSA)
**File:** `terraform/modules/iam/main.tf`
_Purpose: "Least Privilege" security. Pods assume these roles, not the underlying EC2 nodes._

```hcl
# To be populated with Bedrock and S3 access policies in Phase 3
```

---

## Part 5: Verification

### 5.1 Manual Verification Steps

**1. Verify Minikube Status**
```bash
minikube status
# Expect: host, kubelet, apiserver all "Running"

kubectl config current-context
# Expect: minikube
```

**2. Verify Namespace Creation**
```bash
kubectl get namespaces
# Should see: dev

kubectl config view --minify | grep namespace
# Expect: namespace: dev
```

**3. Verify Manifests Applied**
```bash
kubectl get all -n dev
# Should see: deployment, pod, service for rag-api
```

**4. Verify Pod Health**
```bash
# Check pod status
kubectl get pods -n dev
# STATUS should be: Running

# Check logs
kubectl logs -l app=rag-api -n dev --tail=50
# Should see: "Application startup complete"

# Describe pod (check events)
kubectl describe pod -l app=rag-api -n dev
# Events should show: Pulled, Created, Started (no errors)
```

**5. Verify Health Probes**
```bash
# Port forward to access service
kubectl port-forward service/rag-api-service 8080:80 -n dev &

# Test liveness probe
curl http://localhost:8080/health/live
# Expect: {"status": "alive"}

# Test readiness probe
curl http://localhost:8080/health/ready
# Expect: {"status": "ready"}

# Test main health endpoint
curl http://localhost:8080/health
# Expect: {"status": "healthy"}
```

**6. Verify ConfigMap & Secrets**
```bash
# Check ConfigMap
kubectl get configmap rag-api-config -n dev -o yaml
# Verify: APP_ENV, AWS_REGION values

# Check Secret exists (don't expose values)
kubectl get secret rag-api-secrets -n dev
# Should show: 1 item in DATA column
```

**7. Test Image Loading in Minikube**
```bash
# Verify image is in Minikube's docker
eval $(minikube docker-env)
docker images | grep llmops-rag-api
# Should see: llmops-rag-api:latest
```

**8. Verify Terraform Modules (Syntax Only)**
```bash
# Initialize VPC module
cd terraform/modules/vpc
terraform init
terraform validate
# Expect: Success! The configuration is valid.

# Initialize EKS module
cd ../eks
terraform init
terraform validate
# Expect: Success! The configuration is valid.
```

### 5.2 Verification Checklist

### ✅ Local Orchestration
- [ ] Minikube running with `dev` namespace active
- [ ] All manifests in `kubernetes/base/` created
- [ ] Pods running (`kubectl get pods` shows Running)
- [ ] Logs show FastAPI startup successful
- [ ] ConfigMap contains correct environment variables
- [ ] Secret created (placeholder values)
- [ ] Health probes responding correctly
- [ ] `curl localhost:8080/health` returns 200 OK

### ✅ Infrastructure Readiness
- [ ] `terraform/modules/vpc/main.tf` created with VPC configuration
- [ ] `terraform/modules/eks/main.tf` created with EKS cluster config
- [ ] `terraform/modules/iam/main.tf` created (placeholder for Phase 3)
- [ ] `terraform init` passes in all modules (syntax check only)
- [ ] `terraform validate` passes in all modules
- [ ] No `terraform apply` executed (cost savings)

---

**Next Strategic Move:** With the container orchestration validated locally, we will proceed to **Phase 3: Core Application Features**, where we will integrate the "Brains" (AWS Bedrock & Vector DB) into this running logic.
