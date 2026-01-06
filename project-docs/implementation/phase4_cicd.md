# Phase 4: CI/CD Pipeline - Implementation Plan

**Goal:** Automate the entire software delivery lifecycle from code commit to production deployment. Implement quality gates, security scanning, and automated testing to ensure reliable, repeatable deployments.

---

## 🏗️ Architectural Context

Phase 4 establishes **DevOps Excellence** through automation:
1.  **Continuous Integration**: Automated testing, linting, and security scanning on every PR.
2.  **Continuous Deployment**: Automated deployments to dev, manual-gated deployments to staging/prod.
3.  **Data Pipeline Automation**: Auto-sync documents from Git to S3 and vector DB.
4.  **Infrastructure as Code**: Terraform automation with plan/apply workflows.

**Engineering Outcomes:**
- **Continuous Integration**: Automated linting, testing, and Docker builds on every commit.
- **Continuous Deployment**: Zero-touch deployment to Dev; Blue/Green deployment to Production.
- **Security Automation**: Automated vulnerability scanning (Trivy) and secret detection.
- **Infrastructure as Code**: Terraform Plan/Apply workflows integrated into GitHub Actions.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: CI Workflow (Code Quality)](#part-1-ci-workflow-code-quality)**
- [1.1 Linting & Formatting](#11-linting--formatting)
- [1.2 Unit Testing](#12-unit-testing)
- [1.3 Docker Build & Push](#13-docker-build--push)
- [1.4 Security Scanning](#14-security-scanning)

**[Part 2: Data Sync Workflow](#part-2-data-sync-workflow)**
- [2.1 Document Upload Automation](#21-document-upload-automation)
- [2.2 Embedding Generation](#22-embedding-generation)

**[Part 3: CD Workflows](#part-3-cd-workflows)**
- [3.1 Dev Deployment (Auto)](#31-dev-deployment-auto)
- [3.2 Staging Deployment (Manual)](#32-staging-deployment-manual)
- [3.3 Production Deployment (Gated)](#33-production-deployment-gated)

**[Part 4: Infrastructure Automation](#part-4-infrastructure-automation)**
- [4.1 Terraform Plan/Apply](#41-terraform-planapply)

**[Part 5: Branch Protection & Verification](#part-5-branch-protection--verification)**
- [5.1 GitHub Branch Protection Rules](#51-github-branch-protection-rules)
- [5.2 Verification Steps](#52-verification-steps)

---

## Prerequisites

- **Phase 3 Complete**: RAG application functional with all services.
- **GitHub Repository**: With Actions enabled.
- **AWS ECR**: Container registry created.
- **GitHub Secrets**: AWS credentials, ECR URL configured.

---

## Part 1: CI Workflow (Code Quality)

### 1.1 Linting & Formatting
**File:** `.github/workflows/ci.yml`

Complete CI pipeline with quality gates.

```yaml
name: CI - Code Quality & Build

on:
  pull_request:
    branches: [main]
    paths:
      - 'api/**'
      - 'tests/**'
      - 'requirements.txt'
      - 'Dockerfile'

env:
  PYTHON_VERSION: '3.11'

jobs:
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pylint black mypy pytest
          pip install -r requirements.txt
      
      - name: Run Black (Format Check)
        run: black --check api/ tests/
      
      - name: Run Pylint
        run: pylint api/ --fail-under=8.0
      
      - name: Run MyPy (Type Check)
        run: mypy api/ --ignore-missing-imports

  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run Tests with Coverage
        run: |
          pytest tests/ \
            --cov=api \
            --cov-report=xml \
            --cov-report=term \
            --cov-fail-under=70
      
      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  docker-build:
    name: Docker Build & Push
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build Docker Image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: llmops-rag-api
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
                       -t $ECR_REGISTRY/$ECR_REPOSITORY:latest \
                       -f api/Dockerfile .
      
      - name: Run Trivy Security Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.login-ecr.outputs.registry }}/llmops-rag-api:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy Results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
      
      - name: Push to ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: llmops-rag-api
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
      
      - name: Comment PR with Image Details
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `✅ Docker image built and pushed!\n\nImage: \`${{ steps.login-ecr.outputs.registry }}/llmops-rag-api:${{ github.sha }}\``
            })
```

### 1.2 Unit Testing
**File:** `tests/test_rag_service.py`

Example unit test structure.

```python
import pytest
from api.services.rag_service import rag_service
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_rag_query_success():
    """Test successful RAG query"""
    with patch('api.services.vector_store.vector_store') as mock_vector:
        with patch('api.services.llm_service.llm_service') as mock_llm:
            # Mock vector search results
            mock_vector.hybrid_search.return_value = {
                'documents': ['Test document content'],
                'metadatas': [{'domain': 'test'}]
            }
            
            # Mock LLM response
            mock_llm.generate_response.return_value = "Test answer"
            
            # Execute
            result = rag_service.query("test question", domain="test")
            
            # Assert
            assert result['answer'] == "Test answer"
            assert result['domain'] == "test"
            assert 'execution_time_ms' in result

@pytest.mark.asyncio
async def test_rag_query_with_invalid_domain():
    """Test RAG query with access control"""
    # Test implementation here
    pass
```

### 1.3 Docker Build & Push
Covered in the CI workflow above (docker-build job).

### 1.4 Security Scanning
Covered in the CI workflow above (Trivy scan step).

---

## Part 2: Data Sync Workflow

### 2.1 Document Upload Automation
**File:** `.github/workflows/data-sync.yml`

Automatically process documents committed to the repo.

```yaml
name: Data Sync - Document Processing

on:
  push:
    branches: [main]
    paths:
      - 'data/documents/**'

jobs:
  sync-documents:
    name: Sync Documents to S3 & Vector DB
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2  # Get previous commit for diff
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install boto3 requests PyPDF2
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Get Changed Files
        id: changed-files
        run: |
          # Get list of added/modified files in data/documents/
          git diff --name-only --diff-filter=AM HEAD~1 HEAD | \
            grep '^data/documents/' > changed_files.txt || true
          
          echo "Changed files:"
          cat changed_files.txt
      
      - name: Upload to S3 and Trigger Ingestion
        env:
          API_URL: ${{ secrets.API_URL }}
          S3_BUCKET: ${{ secrets.DOCUMENTS_BUCKET }}
        run: |
          python scripts/sync_documents.py \
            --files changed_files.txt \
            --bucket $S3_BUCKET \
            --api-url $API_URL
      
      - name: Verify Ingestion
        run: |
          python scripts/verify_sync.py --files changed_files.txt
```

### 2.2 Embedding Generation
**File:** `scripts/sync_documents.py`

Script to upload documents and trigger embedding generation.

```python
import boto3
import requests
import argparse
from pathlib import Path

def sync_documents(files_list: str, bucket: str, api_url: str):
    s3 = boto3.client('s3')
    
    with open(files_list, 'r') as f:
        files = [line.strip() for line in f if line.strip()]
    
    for file_path in files:
        path = Path(file_path)
        
        # Determine domain from directory structure
        # e.g., data/documents/legal/policy.pdf -> domain=legal
        parts = path.parts
        domain = parts[2] if len(parts) > 2 else 'general'
        
        # Upload to S3
        s3_key = f"documents/{domain}/{path.name}"
        print(f"Uploading {file_path} to s3://{bucket}/{s3_key}")
        
        s3.upload_file(str(path), bucket, s3_key)
        
        # Trigger API ingestion
        with open(file_path, 'rb') as file_data:
            response = requests.post(
                f"{api_url}/documents/upload",
                files={'file': file_data},
                params={'domain': domain}
            )
            
            if response.status_code == 200:
                print(f"✅ {path.name} processed successfully")
            else:
                print(f"❌ {path.name} failed: {response.text}")
                raise Exception(f"Upload failed for {path.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', required=True)
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--api-url', required=True)
    args = parser.parse_args()
    
    sync_documents(args.files, args.bucket, args.api_url)
```

---

## Part 3: CD Workflows

### 3.1 Dev Deployment (Auto)
**File:** `.github/workflows/cd-dev.yml`

Automatic deployment to dev after PR merge.

```yaml
name: CD - Deploy to Dev

on:
  push:
    branches: [main]
    paths:
      - 'api/**'
      - 'kubernetes/**'

jobs:
  deploy-dev:
    name: Deploy to Dev Environment
    runs-on: ubuntu-latest
    environment: development
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --name llmops-rag-cluster \
            --region ap-southeast-2
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Update Deployment Image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          kubectl set image deployment/rag-api \
            api=$ECR_REGISTRY/llmops-rag-api:$IMAGE_TAG \
            -n dev
      
      - name: Wait for Rollout
        run: |
          kubectl rollout status deployment/rag-api -n dev --timeout=5m
      
      - name: Run Smoke Tests
        run: |
          # Get service URL
          API_URL=$(kubectl get svc rag-api-service -n dev -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
          
          # Test health endpoint
          curl -f http://$API_URL/health || exit 1
          
          # Test query endpoint
          curl -f -X POST http://$API_URL/query \
            -H "Content-Type: application/json" \
            -d '{"question": "test", "domain": "general"}' || exit 1
      
      - name: Notify Slack on Success
        if: success()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Deployed to Dev: ${{ github.sha }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 3.2 Staging Deployment (Manual)
**File:** `.github/workflows/cd-staging.yml`

Manual deployment to staging with integration tests.

```yaml
name: CD - Deploy to Staging

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Image tag to deploy (default: latest)'
        required: false
        default: 'latest'

jobs:
  deploy-staging:
    name: Deploy to Staging Environment
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS & kubectl
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --name llmops-rag-cluster \
            --region ap-southeast-2
      
      - name: Deploy to Staging
        run: |
          kubectl set image deployment/rag-api \
            api=${{ secrets.ECR_REGISTRY }}/llmops-rag-api:${{ github.event.inputs.image_tag }} \
            -n staging
          
          kubectl rollout status deployment/rag-api -n staging --timeout=5m
      
      - name: Run Integration Tests
        run: |
          pytest tests/integration/ \
            --env=staging \
            --api-url=${{ secrets.STAGING_API_URL }}
```

### 3.3 Production Deployment (Gated)
**File:** `.github/workflows/cd-production.yml`

Production deployment with manual approval and rollback capability.

```yaml
name: CD - Deploy to Production

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Image tag to deploy'
        required: true
      deployment_strategy:
        description: 'Deployment strategy'
        required: true
        type: choice
        options:
          - rolling
          - blue-green
          - canary

jobs:
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    environment: 
      name: production
      url: https://rag.example.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS & kubectl
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --name llmops-rag-cluster \
            --region ap-southeast-2
      
      - name: Deploy (Rolling Update)
        if: github.event.inputs.deployment_strategy == 'rolling'
        run: |
          kubectl set image deployment/rag-api \
            api=${{ secrets.ECR_REGISTRY }}/llmops-rag-api:${{ github.event.inputs.image_tag }} \
            -n prod
          
          kubectl rollout status deployment/rag-api -n prod --timeout=10m
      
      - name: Deploy (Blue-Green)
        if: github.event.inputs.deployment_strategy == 'blue-green'
        run: |
          # Create green deployment
          kubectl apply -f kubernetes/prod/deployment-green.yaml
          
          # Wait for green to be ready
          kubectl wait --for=condition=available deployment/rag-api-green -n prod --timeout=5m
          
          # Switch service to green
          kubectl patch service rag-api-service -n prod \
            -p '{"spec":{"selector":{"version":"green"}}}'
          
          # Delete blue deployment after verification
          sleep 60
          kubectl delete deployment rag-api-blue -n prod
      
      - name: Health Check
        run: |
          API_URL=${{ secrets.PROD_API_URL }}
          
          for i in {1..5}; do
            if curl -f $API_URL/health; then
              echo "Health check passed"
              exit 0
            fi
            sleep 10
          done
          
          echo "Health check failed"
          exit 1
      
      - name: Rollback on Failure
        if: failure()
        run: |
          echo "Deployment failed, rolling back..."
          kubectl rollout undo deployment/rag-api -n prod
          kubectl rollout status deployment/rag-api -n prod
```

---

## Part 4: Infrastructure Automation

### 4.1 Terraform Plan/Apply
**File:** `.github/workflows/infrastructure.yml`

Automate Terraform changes with plan preview and manual approval.

```yaml
name: Infrastructure - Terraform

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'
  workflow_dispatch:

jobs:
  terraform-plan:
    name: Terraform Plan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Terraform Init
        working-directory: terraform
        run: terraform init
      
      - name: Terraform Format Check
        working-directory: terraform
        run: terraform fmt -check
      
      - name: Terraform Validate
        working-directory: terraform
        run: terraform validate
      
      - name: Terraform Plan
        working-directory: terraform
        run: |
          terraform plan -out=tfplan
          terraform show -no-color tfplan > plan.txt
      
      - name: Comment PR with Plan
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('terraform/plan.txt', 'utf8');
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan\n\`\`\`\n${plan}\n\`\`\``
            })
      
      - name: Upload Plan Artifact
        uses: actions/upload-artifact@v3
        with:
          name: tfplan
          path: terraform/tfplan

  terraform-apply:
    name: Terraform Apply
    runs-on: ubuntu-latest
    needs: terraform-plan
    if: github.event_name == 'workflow_dispatch'
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-southeast-2
      
      - name: Download Plan
        uses: actions/download-artifact@v3
        with:
          name: tfplan
          path: terraform/
      
      - name: Terraform Init
        working-directory: terraform
        run: terraform init
      
      - name: Terraform Apply
        working-directory: terraform
        run: terraform apply tfplan
```

---


## Part 4.5: Integration & Deployment

> **Critical**: This section shows how to activate and test all the CI/CD workflows you created in Parts 1-4.

### 4.5.1 Configure GitHub Secrets

**1. Navigate to GitHub Repository Settings:**
```
https://github.com/YOUR_USERNAME/llmops-rag-pipeline/settings/secrets/actions
```

**2. Add Required Secrets:**

Click "New repository secret" for each:

| Secret Name | Value | Purpose |
|------------|-------|---------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | For Terraform and AWS deployments |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | For Terraform and AWS deployments |
| `DOCKER_USERNAME` | Your Docker Hub username | For pushing images |
| `DOCKER_PASSWORD` | Your Docker Hub token | For pushing images |
| `API_URL` | `https://your-api-url.com` | For data sync workflow |

**3. Verify Secrets are Set:**
```bash
# List secrets via GitHub CLI
gh secret list
```

### 4.5.2 Commit and Push Workflow Files

**1. Add all workflow files:**
```bash
git add .github/workflows/
git status
# Should see: ci.yml, data-sync.yml, deploy-dev.yml, deploy-prod.yml, terraform.yml
```

**2. Commit workflows:**
```bash
git commit -m "ci: add GitHub Actions workflows for CI/CD pipeline

- Added CI workflow for linting and testing
- Added data sync workflow for document ingestion
- Added deployment workflows for dev and prod
- Added Terraform automation workflow"
```

**3. Push to trigger workflows:**
```bash
git push origin main
```

### 4.5.3 Verify Workflows Appear in GitHub Actions

**1. Check Actions tab:**
```
https://github.com/YOUR_USERNAME/llmops-rag-pipeline/actions
```

You should see:
- ✅ CI Pipeline
- ✅ Data Sync
- ✅ Deploy to Dev
- ✅ Deploy to Prod
- ✅ Terraform Plan/Apply

**2. Monitor first run:**
The CI workflow should trigger automatically on push. Watch it complete.

### 4.5.4 Test CI Workflow Manually

**1. Trigger via GitHub UI:**
- Go to Actions → CI Pipeline → Run workflow
- Select branch: `main`
- Click "Run workflow"

**2. Or trigger via CLI:**
```bash
gh workflow run ci.yml
```

**3. Watch the workflow:**
```bash
gh run watch
```

**4. Expected output:**
```
✓ Lint (Python)
✓ Lint (Terraform)
✓ Test (Unit Tests)
✓ Build Docker Image
```

### 4.5.5 Test Data Sync Workflow

**1. Add a test document:**
```bash
mkdir -p data/documents
echo "Test document for sync" > data/documents/test.txt
git add data/documents/test.txt
git commit -m "test: add sample document for sync workflow"
git push origin main
```

**2. Verify workflow triggered:**
```bash
gh run list --workflow=data-sync.yml
# Should show a recent run
```

**3. Check workflow logs:**
```bash
gh run view --log
# Should see: "Sync to API" step with POST requests
```

### 4.5.6 Configure Branch Protection

**1. Run the setup script:**
```bash
chmod +x scripts/setup_branch_protection.sh
./scripts/setup_branch_protection.sh
```

**2. Or configure manually via GitHub UI:**
```
Settings → Branches → Add rule
Branch name pattern: main
☑ Require status checks to pass before merging
  ☑ lint
  ☑ test
  ☑ docker-build
☑ Require pull request reviews before merging
  Required approvals: 1
```

**3. Verify protection is active:**
```bash
gh api repos/:owner/:repo/branches/main/protection | jq '.required_status_checks'
```

### 4.5.7 Test the Full CI/CD Flow

**1. Create a feature branch:**
```bash
git checkout -b feature/test-cicd
```

**2. Make a change:**
```bash
echo "# CI/CD Test" >> README.md
git add README.md
git commit -m "test: verify CI/CD pipeline"
git push origin feature/test-cicd
```

**3. Create a Pull Request:**
```bash
gh pr create --title "Test CI/CD Pipeline" --body "Testing automated checks"
```

**4. Watch CI checks run:**
```bash
gh pr checks
# Should show: lint ✓, test ✓, docker-build ✓
```

**5. Merge the PR:**
```bash
gh pr merge --squash
```

**6. Verify deployment workflow triggers:**
```bash
gh run list --workflow=deploy-dev.yml
# Should show a run triggered by the merge
```

### 4.5.8 Troubleshooting Common Issues

**Issue: Workflows not appearing**
```bash
# Check if .github/workflows directory exists
ls -la .github/workflows/

# Verify YAML syntax
yamllint .github/workflows/*.yml
```

**Issue: Secrets not accessible**
```bash
# Verify secrets are set at repository level (not environment)
gh secret list

# Check workflow permissions
# Settings → Actions → General → Workflow permissions
# Should be: "Read and write permissions"
```

**Issue: Docker build fails**
```bash
# Test Docker build locally first
docker build -t test -f api/Dockerfile .

# Check if DOCKER_USERNAME and DOCKER_PASSWORD are correct
echo $DOCKER_USERNAME
```

**Issue: Terraform workflow fails**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Terraform backend is configured
cat terraform/backend.tf
```

---

## Part 5: Branch Protection & Verification

### 5.1 GitHub Branch Protection Rules
**File:** `scripts/setup_branch_protection.sh`

Script to configure branch protection via GitHub API.

```bash
#!/bin/bash

# Configure branch protection for main branch
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks[strict]=true \
  --field required_status_checks[contexts][]=lint \
  --field required_status_checks[contexts][]=test \
  --field required_status_checks[contexts][]=docker-build \
  --field enforce_admins=true \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_pull_request_reviews[dismiss_stale_reviews]=true \
  --field restrictions=null

echo "✅ Branch protection configured for main"
```

### 5.2 Verification Steps

**1. Verify CI Workflow**
```bash
# Create a test PR
git checkout -b test/ci-verification
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify CI workflow"
git push origin test/ci-verification

# Create PR and verify:
# - Lint job passes
# - Test job passes
# - Docker build succeeds
# - Trivy scan completes
```

**2. Verify Data Sync**
```bash
# Add a test document
mkdir -p data/documents/test
echo "Test document content" > data/documents/test/sample.txt
git add data/documents/test/sample.txt
git commit -m "docs: add test document"
git push origin main

# Verify in GitHub Actions:
# - Workflow triggers
# - Document uploads to S3
# - API ingestion completes
```

**3. Verify CD Workflows**
```bash
# Trigger staging deployment
gh workflow run cd-staging.yml -f image_tag=latest

# Verify:
# - Deployment succeeds
# - Integration tests pass
# - Staging environment accessible
```

**4. Verify Branch Protection**
```bash
# Try to push directly to main (should fail)
git checkout main
echo "test" >> README.md
git commit -am "test: direct push"
git push origin main
# Expected: Error - branch protection rules

# Verify PR requirements work
# - Create PR
# - Verify status checks are required
# - Verify approval is required
```

---

## Verification Checklist

### ✅ CI Workflow
- [ ] Linting runs on every PR
- [ ] Unit tests execute with coverage reporting
- [ ] Docker images build successfully
- [ ] Trivy security scans complete
- [ ] Images push to ECR
- [ ] PR comments show build status

### ✅ Data Sync
- [ ] Workflow triggers on document changes
- [ ] Documents upload to S3
- [ ] Embeddings generate automatically
- [ ] Vector DB updates successfully

### ✅ CD Workflows
- [ ] Dev deploys automatically on main push
- [ ] Staging deploys on manual trigger
- [ ] Production requires approval
- [ ] Rollback works on failure
- [ ] Health checks validate deployments

### ✅ Infrastructure
- [ ] Terraform plan runs on PR
- [ ] Plan output comments on PR
- [ ] Apply requires manual approval
- [ ] State stored in S3 backend

### ✅ Branch Protection
- [ ] Direct pushes to main blocked
- [ ] PR approval required
- [ ] Status checks must pass
- [ ] Stale reviews dismissed

---

**Next Strategic Move:** With CI/CD automation in place, we proceed to **Phase 5: Monitoring & Observability** to instrument the application with metrics, logs, and alerting for production readiness.
