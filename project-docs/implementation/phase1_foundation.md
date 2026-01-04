# Phase 1: Foundation - Implementation Plan
  
**Goal:** Set up local development environment, create basic FastAPI application, configure AWS prerequisites, and initialize Terraform infrastructure

---

## Overview

Phase 1 establishes the foundation for the entire project. We'll follow the **Console → Terraform → Verify** approach documented in `implementation_methodology.md`.

**What We'll Build:**
- Local development environment
- Basic FastAPI application with health checks
- AWS account setup and configuration
- Terraform infrastructure foundation (S3, IAM, VPC basics)

**What We'll Learn:**
- AWS Console navigation
- Terraform basics
- FastAPI application structure
- Docker containerization

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Local Development Environment](#part-1-local-development-environment)**
- [1.1 Install Docker and Docker Compose](#step-11-install-docker-and-docker-compose)
- [1.2 Install Kubernetes Tools (minikube)](#step-12-install-kubernetes-tools-minikube)
- [1.3 Install Terraform](#step-13-install-terraform)
- [1.4 Set Up Python Virtual Environment](#step-14-set-up-python-virtual-environment)
- [1.5 Install AWS CLI](#step-15-install-aws-cli)

**[Part 2: AWS Account Setup](#part-2-aws-account-setup)**
- [2.1 Create AWS Account](#step-21-create-aws-account-if-needed)
- [2.2 Create IAM User](#step-22-create-iam-user-console-walkthrough)
- [2.3 Configure AWS CLI](#step-23-configure-aws-cli)
- [2.4 Create S3 Bucket for Terraform State](#step-24-create-s3-bucket-for-terraform-state-console) *(Optional)*
- [2.5 Create S3 Bucket for Documents](#step-25-create-s3-bucket-for-documents-console) *(Optional)*

**[Part 3: Terraform Setup](#part-3-terraform-setup)**
- [3.1 Create Terraform Directory Structure](#step-31-create-terraform-directory-structure)
- [3.2 Create Terraform Backend Configuration](#step-32-create-terraform-backend-configuration)
- [3.3 Create S3 Module](#step-33-create-s3-module-terraform)
- [3.4 Create Dev Environment Configuration](#step-34-create-dev-environment-configuration)
- [3.5 Initialize and Apply Terraform](#step-35-initialize-and-apply-terraform)
- [3.6 Verify Terraform-Created Resources](#step-36-verify-terraform-created-resources-console)
- [3.7 Clean Up Manual Resources](#step-37-clean-up-manual-resources-if-applicable) *(If Applicable)*

**[Part 4: Basic FastAPI Application](#part-4-basic-fastapi-application)**
- [4.1 Create API Directory Structure](#step-41-create-api-directory-structure)
- [4.2 Create Requirements File](#step-42-create-requirements-file)
- [4.3 Create Configuration](#step-43-create-configuration)
- [4.4 Create Health Check Router](#step-44-create-health-check-router)
- [4.5 Create Main Application](#step-45-create-main-application)
- [4.6 Test FastAPI Application](#step-46-test-fastapi-application)
- [4.7 Create Dockerfile](#step-47-create-dockerfile)
- [4.8 Build and Test Docker Image](#step-48-build-and-test-docker-image)

**[Part 5: Verification Checklist](#part-5-verification-checklist)**

**[Next Steps](#next-steps)**

**[Troubleshooting](#troubleshooting)**

---

## Prerequisites

### Required Software
- macOS (your current OS)
- Homebrew (package manager)
- Git (already installed)
- GitHub account (already set up)

### Time Estimate
- **Console walkthroughs:** 2-3 hours
- **Terraform setup:** 2-3 hours
- **FastAPI development:** 3-4 hours
- **Testing and verification:** 1-2 hours
- **Total:** ~8-12 hours

---

## Part 1: Local Development Environment

### Step 1.1: Install Docker and Docker Compose

**Why:** Containerize the FastAPI application for consistent environments

**Installation:**

```bash
# Install Docker Desktop for Mac
brew install --cask docker

# Verify installation
docker --version
docker-compose --version

# Start Docker Desktop (from Applications)
open -a Docker
```

**Verification:**
```bash
# Test Docker
docker run hello-world

# Should see: "Hello from Docker!"
```

**Expected Output:**
```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

---

### Step 1.2: Install Kubernetes Tools (minikube)

**Why:** Test Kubernetes deployments locally before deploying to EKS

**Installation:**

```bash
# Install minikube
brew install minikube

# Install kubectl
brew install kubectl

# Install helm (for package management)
brew install helm

# Verify installations
minikube version
kubectl version --client
helm version
```

**Start minikube:**
```bash
# Start local Kubernetes cluster
minikube start --driver=docker --cpus=2 --memory=4096

# Verify cluster is running
kubectl cluster-info
kubectl get nodes
```

**Expected Output:**
```
✅ minikube v1.32.0 on Darwin
✅ Using the docker driver
✅ Done! kubectl is now configured to use "minikube" cluster
```

---

### Step 1.2.1: Understanding minikube Lifecycle & Data Persistence

**Important:** minikube runs as a Docker container and uses resources (CPU/RAM) only when running. Understanding how to manage it is crucial for daily development.

#### **minikube Lifecycle:**

**Check Status:**
```bash
minikube status

# Output when running:
# minikube
# type: Control Plane
# host: Running
# kubelet: Running
# apiserver: Running
```

**Stop Cluster** (frees 4 GB RAM, 2 CPUs):
```bash
minikube stop

# ✋  Stopping node "minikube"  ...
# 🛑  1 node stopped.

# Resources freed, data preserved
```

**Start Cluster** (resumes in ~30 seconds):
```bash
minikube start

# Everything restored automatically
```

**Delete Cluster** (complete removal):
```bash
minikube delete

# Only do this if you want to start fresh
# All data will be lost
```

#### **What Persists After Stop/Start:**

**✅ Preserved:**
- All Kubernetes deployments
- Services and configurations
- ConfigMaps and Secrets
- PersistentVolume data
- Docker images (cached)

**❌ Not Preserved:**
- Running pods (but they restart automatically)
- Temporary data in `/tmp`
- In-memory cache (unless persisted)

#### **Daily Development Workflow:**

```bash
# Morning - Start work
minikube start              # 30 seconds
kubectl get pods            # Check your apps

# Work on your code...
kubectl apply -f app.yaml   # Deploy changes

# Evening - Done for the day
minikube stop               # Free resources
```

#### **Resource Usage:**

**When Running:**
- Uses 4 GB RAM
- Uses 2 CPU cores
- Container visible in `docker ps`

**When Stopped:**
- Uses 0 GB RAM
- Uses 0 CPU cores
- Container stopped (not visible in `docker ps`)

#### **Best Practices:**

**Stop minikube when:**
- ❌ Not working on the project
- ❌ Need more RAM for other apps
- ❌ Done for the day

**Keep minikube running when:**
- ✅ Actively developing
- ✅ Testing deployments
- ✅ Running Phases 2-6

**For This Project:**
- **Phase 1:** Can stop after verification
- **Phases 2-6:** Start when working, stop when done
- **Phase 7:** Optional (we'll use AWS EKS)

---

### Step 1.3: Install Terraform

**Why:** Infrastructure as Code for AWS resources

**Installation:**

```bash
# Install Terraform
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Verify installation
terraform version
```

**Expected Output:**
```
Terraform v1.7.0
```

---

### Step 1.4: Set Up Python Virtual Environment

**Why:** Isolate project dependencies

**Setup:**

```bash
# Navigate to project directory
cd /Users/Ashish/GitHub\ Repos/llmops-rag-pipeline

# Create virtual environment with Python 3.12
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.12.3

# Upgrade pip
pip install --upgrade pip

# Verify
which python  # Should show path to .venv/bin/python
```

**Expected Output:**
```
Python 3.11.x
/Users/Ashish/GitHub Repos/llmops-rag-pipeline/.venv/bin/python
```

**Note:** Always activate `.venv` before working on the project:
```bash
source .venv/bin/activate
```

---

### Step 1.5: Install AWS CLI

**Why:** Interact with AWS services from command line

**Installation:**

```bash
# Install AWS CLI
brew install awscli

# Verify installation
aws --version
```

**Expected Output:**
```
aws-cli/2.15.0 Python/3.11.x Darwin/xx.x.x
```

---

## Part 2: AWS Account Setup

> **Note:** Steps 2.4 and 2.5 include **optional** manual Console walkthroughs for learning purposes. If you're already familiar with AWS Console or want to skip directly to Terraform, you can:
> - **Skip to Part 3** (Terraform Setup) and let Terraform create all resources
> - **Come back later** if you want to understand Console → Terraform mapping
> 
> The Terraform code in Part 3 will create all necessary resources regardless of whether you do the manual steps.

### Step 2.1: Create AWS Account (If Needed)

**If you don't have an AWS account:**

1. Go to https://aws.amazon.com
2. Click "Create an AWS Account"
3. Follow the signup process
4. Verify email and phone
5. Add payment method (credit card)
6. Choose Free Tier plan

**Cost Note:** We'll use Free Tier where possible, but some services will incur costs (~$200-290 total for 8 weeks)

---

### Step 2.2: Create IAM User (Console Walkthrough)

**Why:** Don't use root account for daily operations

**Console Steps:**

1. **Sign in to AWS Console**
   - Go to https://console.aws.amazon.com
   - Sign in with root account

2. **Navigate to IAM**
   - Search for "IAM" in the top search bar
   - Click "IAM" (Identity and Access Management)

3. **Create User**
   - Click "Users" in left sidebar
   - Click "Create user"
   - User name: `llmops-admin`
   - Click "Next"

4. **Set Permissions**
   - Select "Attach policies directly"
   - Search and select:
     - `AdministratorAccess` (for now, we'll restrict later)
   - Click "Next"

5. **Review and Create**
   - Review settings
   - Click "Create user"

6. **Create Access Keys**
   - Click on the newly created user `llmops-admin`
   - Go to "Security credentials" tab
   - Scroll to "Access keys"
   - Click "Create access key"
   - Use case: "Command Line Interface (CLI)"
   - Check "I understand" checkbox
   - Click "Next"
   - Description: "Local development"
   - Click "Create access key"
   - **IMPORTANT:** Download the CSV file or copy both:
     - Access key ID
     - Secret access key
   - Click "Done"

**Security Note:** Never commit these keys to Git!

---

### Step 2.3: Configure AWS CLI

**Configure credentials:**

```bash
# Configure AWS CLI
aws configure

# Enter when prompted:
# AWS Access Key ID: <your-access-key-id>
# AWS Secret Access Key: <your-secret-access-key>
# Default region name: ap-southeast-2
# Default output format: json
```

**Verify configuration:**

```bash
# Test AWS CLI
aws sts get-caller-identity

# Should show your user details
```

**Expected Output:**
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/llmops-admin"
}
```

---

### Step 2.3.1: Verify Bedrock Model Availability

**Why:** Ensure AWS Bedrock models (Nova 2, Titan Embeddings) are available in your region

**Check availability:**

```bash
# List Amazon Bedrock models in your region
aws bedrock list-foundation-models --region ap-southeast-2 --query 'modelSummaries[?contains(modelId, `amazon`)].[modelId]' --output table

# Replace ap-southeast-2 with your region if different
```

**Expected Output:**
```
-----------------------------------
|      ListFoundationModels       |
+---------------------------------+
|  amazon.nova-2-lite-v1:0        |  ← For simple queries
|  amazon.nova-pro-v1:0           |  ← For complex queries
|  amazon.titan-embed-text-v2:0   |  ← For embeddings
|  amazon.titan-embed-image-v1:0  |
|  amazon.nova-lite-v1:0          |
|  amazon.nova-micro-v1:0         |
+---------------------------------+
```

**Required Models:**
- ✅ `amazon.nova-2-lite-v1:0` or `amazon.nova-lite-v1:0` (cost-effective LLM)
- ✅ `amazon.nova-pro-v1:0` (high-quality LLM)
- ✅ `amazon.titan-embed-text-v2:0` (text embeddings)

**If models are NOT available in your region:**
- Option 1: Use `us-east-1` (if models not available in your region)
- Option 2: Check [AWS Bedrock regions](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-regions.html)
- Option 3: Use a different region where models are available

**Update region if needed:**
```bash
# If you need to change region
aws configure set region us-east-1

# Verify again
aws bedrock list-foundation-models --region us-east-1 --query 'modelSummaries[?contains(modelId, `amazon`)].[modelId]' --output table
```

---

### Step 2.4: Create S3 Bucket for Terraform State (Console)

**Why:** Store Terraform state remotely for team collaboration and safety

> **💡 Optional Learning Step:** This walkthrough shows you how to create S3 buckets in the Console. If you prefer, you can **skip this** and let Terraform create the bucket in Part 3. However, doing it manually first helps you understand what Terraform is doing behind the scenes.
>
> **To skip:** Jump to [Part 3: Terraform Setup](#part-3-terraform-setup)

**Console Steps:**

1. **Navigate to S3**
   - Search for "S3" in AWS Console
   - Click "S3"

2. **Create Bucket**
   - Click "Create bucket"
   - Bucket name: `llmops-rag-terraform-state`
     - Must be globally unique (add suffix if needed)
   - Region: `ap-southeast-2`
   - **Block Public Access:** Keep all checkboxes CHECKED (block all public access)
   - **Bucket Versioning:** Enable
   - **Encryption:** Enable (Server-side encryption with Amazon S3 managed keys)
   - **Tags:**
     - Key: `Project`, Value: `LLMOps`
     - Key: `Purpose`, Value: `Terraform State`
   - Click "Create bucket"

3. **Verify Bucket**
   - Find your bucket in the list
   - Click on it
   - Check "Properties" tab:
     - Versioning: Enabled ✅
     - Encryption: Enabled ✅

**Note the bucket name** - you'll need it for Terraform configuration.

---

### Step 2.5: Create S3 Bucket for Documents (Console)

**Why:** Store uploaded documents

> **💡 Optional Learning Step:** This is for learning how Console settings map to Terraform code. If you've already done this in other projects or want to skip ahead, you can **skip this** and go directly to Part 3 where Terraform will create the production bucket.
>
> **To skip:** Jump to [Part 3: Terraform Setup](#part-3-terraform-setup)

**Important:** We'll add `-manual` suffix to distinguish from Terraform-managed resources.

**Console Steps:**

1. **Create Bucket**
   - Click "Create bucket"
   - Bucket name: `llmops-rag-documents-dev-<your-initials>-manual`
     - Example: `llmops-rag-documents-dev-manual`
     - **Note the `-manual` suffix** - for learning/comparison only
   - Region: `ap-southeast-2`
   - **Block Public Access:** Keep all checkboxes CHECKED
   - **Bucket Versioning:** Enable
   - **Encryption:** Enable
   - **Tags:**
     - Key: `Project`, Value: `LLMOps`
     - Key: `Environment`, Value: `dev`
     - Key: `Purpose`, Value: `Learning-Manual`
   - Click "Create bucket"

2. **Configure Lifecycle Policy** (Cost Optimization)
   - Click on the bucket
   - Go to "Management" tab
   - Click "Create lifecycle rule"
   - Rule name: `transition-to-ia`
   - Rule scope: Apply to all objects
   - **Lifecycle rule actions:**
     - Check "Transition current versions of objects between storage classes"
     - Add transition:
       - Days after object creation: `30`
       - Storage class: `Standard-IA`
     - Add transition:
       - Days after object creation: `90`
       - Storage class: `Glacier Flexible Retrieval`
   - Click "Create rule"

**Verify:**
- Bucket created ✅
- Versioning enabled ✅
- Lifecycle rule active ✅

---

## Part 3: Terraform Setup

### Step 3.1: Create Terraform Directory Structure

**Create folders:**

```bash
# Navigate to project root
cd /Users/Ashish/GitHub\ Repos/llmops-rag-pipeline

# Create Terraform structure
mkdir -p terraform/modules/{s3,iam,vpc,eks,monitoring}
mkdir -p terraform/environments/{dev,staging,prod}

# Verify structure
tree terraform/
```

---

### Step 3.2: Create Terraform Backend Configuration

**Why:** Store Terraform state in S3 (not locally)

**Create file:** `terraform/backend.tf`

```hcl
# terraform/backend.tf

terraform {
  backend "s3" {
    bucket         = "llmops-rag-terraform-state"
    key            = "llmops-rag/terraform.tfstate"
    region         = "ap-southeast-2"
    encrypt        = true
    dynamodb_table = "llmops-rag-terraform-state-lock"  # We'll create this later
  }
  
  required_version = ">= 1.7.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
  
  default_tags {
    tags = {
      Project     = "LLMOps"
      ManagedBy   = "Terraform"
      Environment = "dev"
    }
  }
}
```

**Note:** The DynamoDB table for state locking will be created manually in Step 3.4.1 (Bootstrap). This avoids the chicken-and-egg problem of Terraform needing resources that don't exist yet.

---

### Step 3.3: Create S3 Module (Terraform)

**Why:** Replicate what we created manually in Console

**Create file:** `terraform/modules/s3/main.tf`

```hcl
# terraform/modules/s3/main.tf
# Resources only - production-grade structure

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  
  tags = {
    Name        = var.bucket_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count  = var.enable_lifecycle ? 1 : 0
  bucket = aws_s3_bucket.this.id
  
  rule {
    id     = "transition-to-ia"
    status = "Enabled"
    
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}
```

---

**Create file:** `terraform/modules/s3/variables.tf`

```hcl
# terraform/modules/s3/variables.tf
# Input variables - defines module interface

variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "enable_lifecycle" {
  description = "Enable lifecycle policies for cost optimization"
  type        = bool
  default     = true
}
```

---

**Create file:** `terraform/modules/s3/outputs.tf`

```hcl
# terraform/modules/s3/outputs.tf
# Output values - what the module exposes

output "bucket_name" {
  description = "Name of the created S3 bucket"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "ARN of the created S3 bucket"
  value       = aws_s3_bucket.this.arn
}
```

**Why three files?**
- ✅ Industry best practice
- ✅ Clear separation of concerns
- ✅ Easy to find variables and outputs
- ✅ Better for code reviews
- ✅ Production-grade structure

---

### Step 3.4: Create Dev Environment Configuration

**Create file:** `terraform/environments/dev/main.tf`

```hcl
# terraform/environments/dev/main.tf

terraform {
  required_version = ">= 1.7.0"
}

module "documents_bucket" {
  source = "../../modules/s3"
  
  bucket_name      = "llmops-rag-documents-dev"  # Replace with your bucket name
  environment      = "dev"
  enable_lifecycle = true
}

output "documents_bucket_name" {
  value = module.documents_bucket.bucket_name
}
```

**Create file:** `terraform/environments/dev/variables.tf`

```hcl
# terraform/environments/dev/variables.tf

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "llmops-rag"
}
```

**Create file:** `terraform/environments/dev/terraform.tfvars`

```hcl
# terraform/environments/dev/terraform.tfvars

aws_region   = "ap-southeast-2"
project_name = "llmops-rag"
```

---

### Step 3.4.1: Bootstrap Backend Resources

**Why:** The S3 bucket and DynamoDB table must exist BEFORE running `terraform init` because the backend configuration references them.

**This is a one-time setup step.**

#### **Option 1: Automated Script (Recommended)**

```bash
# Run the bootstrap script
./scripts/bootstrap-backend.sh
```

**What the script does:**
- ✅ Creates S3 bucket: `llmops-rag-terraform-state`
- ✅ Enables versioning, encryption, and blocks public access
- ✅ Creates DynamoDB table: `llmops-rag-terraform-state-lock`
- ✅ Waits for resources to be ready
- ✅ Verifies everything is configured correctly
- ✅ Handles errors and checks if resources already exist

**Expected Output:**
```
=========================================
Terraform Backend Bootstrap
=========================================

This script will create:
  - S3 bucket: llmops-rag-terraform-state
  - DynamoDB table: llmops-rag-terraform-state-lock
  - Region: ap-southeast-2

Continue? (y/n) y

Step 1: Creating S3 bucket for Terraform state...
==================================================
✅ S3 bucket created: llmops-rag-terraform-state
Enabling versioning...
✅ Versioning enabled
Enabling encryption...
✅ Encryption enabled
Blocking public access...
✅ Public access blocked

Step 2: Creating DynamoDB table for state locking...
=====================================================
✅ DynamoDB table created: llmops-rag-terraform-state-lock
Waiting for table to become active...
✅ DynamoDB table is active

Step 3: Verifying resources...
===============================
S3 bucket: ✅ llmops-rag-terraform-state
Versioning: ✅ Enabled
DynamoDB table: ✅ llmops-rag-terraform-state-lock (ACTIVE)

=========================================
✅ Bootstrap Complete!
=========================================

Backend resources are ready:
  - S3 bucket: llmops-rag-terraform-state
  - DynamoDB table: llmops-rag-terraform-state-lock

You can now run:
  cd terraform/environments/dev
  terraform init
  terraform apply
```

---

#### **Option 2: Manual Commands (If Script Fails)**

<details>
<summary>Click to expand manual commands</summary>

```bash
# Create the bucket
aws s3 mb s3://llmops-rag-terraform-state --region ap-southeast-2

# Enable versioning (required for state safety)
aws s3api put-bucket-versioning \
  --bucket llmops-rag-terraform-state \
  --versioning-configuration Status=Enabled \
  --region ap-southeast-2

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket llmops-rag-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }' \
  --region ap-southeast-2

# Block public access
aws s3api put-public-access-block \
  --bucket llmops-rag-terraform-state \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
  --region ap-southeast-2
```

**Expected Output:**
```
make_bucket: llmops-rag-terraform-state
```

---

#### **Create DynamoDB Table for State Locking**

```bash
aws dynamodb create-table \
  --table-name llmops-rag-terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-southeast-2 \
  --tags Key=Project,Value=LLMOps Key=Purpose,Value=TerraformStateLock
```

**Expected Output:**
```json
{
    "TableDescription": {
        "TableName": "llmops-rag-terraform-state-lock",
        "TableStatus": "CREATING",
        ...
    }
}
```

**Wait for table to be active:**
```bash
aws dynamodb wait table-exists \
  --table-name llmops-rag-terraform-state-lock \
  --region ap-southeast-2

echo "DynamoDB table is ready!"
```

---

#### **Verify Bootstrap Resources**

```bash
# Verify S3 bucket
aws s3 ls | grep llmops-rag-terraform-state
# Should show: llmops-rag-terraform-state

# Verify bucket versioning
aws s3api get-bucket-versioning \
  --bucket llmops-rag-terraform-state \
  --region ap-southeast-2
# Should show: "Status": "Enabled"

# Verify DynamoDB table
aws dynamodb describe-table \
  --table-name llmops-rag-terraform-state-lock \
  --region ap-southeast-2 \
  --query 'Table.TableStatus'
# Should show: "ACTIVE"
```

**What you should see:**
- ✅ S3 bucket: `llmops-rag-terraform-state` exists
- ✅ Versioning: Enabled
- ✅ Encryption: Enabled
- ✅ DynamoDB table: `llmops-rag-terraform-state-lock` is ACTIVE

**Why this step is needed:**
- Terraform backend needs these resources to exist
- Can't create them with Terraform (chicken-and-egg problem)
- One-time manual setup, then Terraform manages everything else
- These resources persist even after `terraform destroy` (perfect for pause/resume)

</details>

---

### Step 3.5: Initialize and Apply Terraform

**Initialize Terraform:**

```bash
cd terraform/environments/dev

# Initialize Terraform (downloads providers)
terraform init

# Expected output: "Terraform has been successfully initialized!"
```

**Plan changes:**

```bash
# See what Terraform will create
terraform plan

# Review the output - should show S3 bucket resources
```

**Apply changes:**

```bash
# Create the resources
terraform apply

# Type 'yes' when prompted
```

**Expected Output:**
```
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:
documents_bucket_name = "llmops-rag-documents-dev"
```

---

### Step 3.6: Verify Terraform-Created Resources (Console)

**Console Verification:**

1. Go to AWS Console → S3
2. Check what buckets exist:

**If you did the manual steps (Step 2.5):**
- You should see **TWO** buckets:
  - `llmops-rag-documents-dev-manual` (created manually)
  - `llmops-rag-documents-dev` (created by Terraform)
- **Compare both** to see how Console settings map to Terraform code
- Proceed to Step 3.7 for cleanup

**If you skipped the manual steps:**
- You should see **ONE** bucket:
  - `llmops-rag-documents-dev` (created by Terraform)
- Verify it has all the features:
  - Versioning: Enabled ✅
  - Encryption: Enabled ✅
  - Public access: Blocked ✅
  - Lifecycle rule: Active ✅
- **Skip Step 3.7** (no manual resources to clean up)

**Learning Point:** 
- If you did manual steps: See how Console actions → Terraform code
- If you skipped: Terraform created everything automatically from code

---

### Step 3.7: Clean Up Manual Resources (If Applicable)

> **Note:** Only do this if you created manual resources in Step 2.5. If you skipped the manual steps, skip this section too.

**Why:** Keep only Terraform-managed resources to avoid:
- Duplicate costs
- Confusion about which is production
- Manual drift (changes not tracked in code)

**Delete Manual Bucket:**

**Option 1: AWS Console**
1. Go to AWS Console → S3
2. Find bucket: `llmops-rag-documents-dev-manual`
3. Select the bucket (checkbox)
4. Click "Delete"
5. Type the bucket name to confirm
6. Click "Delete bucket"

**Option 2: AWS CLI**
```bash
# Delete manual bucket
aws s3 rb s3://llmops-rag-documents-dev-manual --force

# Verify it's gone
aws s3 ls | grep manual
# Should return nothing
```

**Verify Cleanup:**
```bash
# List remaining buckets
aws s3 ls

# Should see:
# - llmops-rag-terraform-state (Terraform state)
# - llmops-rag-documents-dev (Terraform-managed)
# Should NOT see: -manual bucket
```

**What to Keep:**
- ✅ `llmops-terraform-state-*` (Terraform state bucket)
- ✅ `llmops-rag-documents-dev-*` (Terraform-managed, no -manual suffix)

**What to Delete:**
- ❌ `llmops-rag-documents-dev-*-manual` (Console-created)

---

## Part 4: Basic FastAPI Application

### Step 4.1: Create API Directory Structure

```bash
# Navigate to project root
cd /Users/Ashish/GitHub\ Repos/llmops-rag-pipeline

# Create API structure
mkdir -p api/{routers,services,models,utils}
touch api/__init__.py
touch api/{routers,services,models,utils}/__init__.py
```

---

### Step 4.2: Create Requirements File

**Create file:** `api/requirements.txt`

```txt
# FastAPI and server
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0

# AWS
boto3==1.34.0

# Development
pytest==7.4.3
httpx==0.26.0
```

**Install dependencies:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r api/requirements.txt

# Verify
pip list | grep fastapi
```

---

### Step 4.3: Create Configuration

**Create file:** `api/config.py`

```python
# api/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "LLMOps RAG Pipeline"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # AWS
    aws_region: str = "ap-southeast-2"
    documents_bucket: str = "llmops-rag-documents-dev"  # Replace with your bucket
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

### Step 4.4: Create Health Check Router

**Create file:** `api/routers/health.py`

```python
# api/routers/health.py

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    # TODO: Check connections (Redis, Vector DB, AWS)
    return {
        "status": "ready",
        "checks": {
            "api": "ok",
            # "redis": "ok",
            # "vector_db": "ok",
            # "aws": "ok"
        }
    }

@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}
```

---

### Step 4.5: Create Main Application

**Create file:** `api/main.py`

```python
# api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.routers import health

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-based Q&A system with MLOps best practices"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LLMOps RAG Pipeline",
        "version": settings.app_version,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### Step 4.6: Test FastAPI Application

**Run the application:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Run FastAPI
cd /Users/Ashish/GitHub\ Repos/llmops-rag-pipeline
python -m uvicorn api.main:app --reload

# Should see:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Test endpoints:**

```bash
# In a new terminal

# Test root endpoint
curl http://localhost:8000/

# Test health check
curl http://localhost:8000/health/

# Test readiness
curl http://localhost:8000/health/ready

# Test liveness
curl http://localhost:8000/health/live
```

**Expected Responses:**
```json
// Root
{"message":"Welcome to LLMOps RAG Pipeline","version":"0.1.0","docs":"/docs"}

// Health
{"status":"healthy","timestamp":"2026-01-04T13:00:00.000000"}

// Ready
{"status":"ready","checks":{"api":"ok"}}

// Live
{"status":"alive"}
```

**Interactive Docs:**
- Open browser: http://localhost:8000/docs
- See Swagger UI with all endpoints
- Try them out interactively

---

### Step 4.7: Create Dockerfile

**Create file:** `api/Dockerfile`

```dockerfile
# api/Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Step 4.8: Build and Test Docker Image

**Build image:**

```bash
# Navigate to project root
cd /Users/Ashish/GitHub\ Repos/llmops-rag-pipeline

# Build Docker image
docker build -t llmops-rag-api:latest -f api/Dockerfile .

# Verify image
docker images | grep llmops-rag-api
```

**Run container:**

```bash
# Run container
docker run -d -p 8000:8000 --name rag-api llmops-rag-api:latest

# Check if running
docker ps

# Test endpoint
curl http://localhost:8000/health/

# View logs
docker logs rag-api

# Stop and remove container
docker stop rag-api
docker rm rag-api
```

---

## Part 5: Verification Checklist

### ✅ Local Environment

- [ ] Docker installed and running
- [ ] minikube cluster running
- [ ] kubectl configured
- [ ] Terraform installed
- [ ] Python 3.11+ virtual environment created
- [ ] AWS CLI installed and configured

### ✅ AWS Setup

- [ ] IAM user created (`llmops-admin`)
- [ ] Access keys generated and configured
- [ ] S3 bucket for Terraform state created
- [ ] *(Optional)* S3 bucket for documents created manually
- [ ] *(Optional)* Lifecycle policies configured manually

### ✅ Terraform

- [ ] Terraform initialized
- [ ] S3 module created
- [ ] Dev environment configured
- [ ] `terraform apply` successful
- [ ] Resources visible in AWS Console
- [ ] *(If manual steps done)* Manual vs Terraform buckets compared
- [ ] *(If manual steps done)* Manual resources deleted (cleanup complete)
- [ ] Only Terraform-managed resources remain

### ✅ FastAPI Application

- [ ] API structure created
- [ ] Dependencies installed
- [ ] Health check endpoints working
- [ ] Application runs locally
- [ ] Interactive docs accessible
- [ ] Docker image builds successfully
- [ ] Container runs successfully

---

## Next Steps

**After completing Phase 1:**

1. **Mark tasks complete** in `project-docs/tasks.md`
2. **Update progress** (Planning & Documentation → 100%)
3. **Commit all code** to GitHub
4. **Move to Phase 2:** Kubernetes Setup

**Phase 2 Preview:**
- Deploy API to local Kubernetes (minikube)
- Create Kubernetes manifests
- Test health checks with K8s probes
- Prepare EKS Terraform module (don't apply yet)

---

## Troubleshooting

### Docker Issues

**Problem:** Docker daemon not running
```bash
# Solution: Start Docker Desktop
open -a Docker
```

**Problem:** Permission denied
```bash
# Solution: Add user to docker group (may require restart)
sudo usermod -aG docker $USER
```

### Terraform Issues

**Problem:** Backend initialization failed
```bash
# Solution: Verify S3 bucket exists and you have access
aws s3 ls s3://llmops-rag-terraform-state
```

**Problem:** Provider download failed
```bash
# Solution: Clear cache and retry
rm -rf .terraform
terraform init
```

### FastAPI Issues

**Problem:** Module not found
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip install -r api/requirements.txt
```

**Problem:** Port already in use
```bash
# Solution: Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

---

## Summary

**What We Accomplished:**
- ✅ Set up complete local development environment
- ✅ Configured AWS account and IAM
- ✅ Created S3 buckets (Console + Terraform)
- ✅ Learned Console → Terraform mapping
- ✅ Built basic FastAPI application
- ✅ Containerized with Docker
- ✅ Verified everything works

**What We Learned:**
- AWS Console navigation
- Terraform basics and modules
- FastAPI application structure
- Docker containerization
- Infrastructure as Code principles

**Ready for Phase 2!** 🚀
