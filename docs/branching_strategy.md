# Branching and Workflow Strategy

## Overview

This project uses **GitHub Flow** - a simple, PR-based branching strategy that is industry-standard and emphasizes continuous deployment.

---

## Branching Model

### **Single Long-Lived Branch:**
- `main` - Production-ready code, protected, always deployable

### **Short-Lived Feature Branches:**
- `feature/*` - New features (e.g., `feature/add-caching`)
- `bugfix/*` - Bug fixes (e.g., `bugfix/fix-embeddings`)
- `hotfix/*` - Critical fixes (e.g., `hotfix/security-patch`)
- `docs/*` - Documentation/data changes (e.g., `docs/add-policies`)

---

## Workflow

### **1. Create Feature Branch**

```bash
# Start from latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/add-semantic-caching

# Make changes
git add .
git commit -m "Add Redis semantic caching layer"
git push origin feature/add-semantic-caching
```

### **2. Create Pull Request**

- **From**: `feature/add-semantic-caching`
- **To**: `main`
- **Triggers**: CI workflow (build, test, security scan)
- **Requires**: Code review + 1 approval

### **3. CI Runs on PR**

```yaml
# .github/workflows/ci.yml
on:
  pull_request:
    branches: [main]

jobs:
  - Lint code (pylint, black, mypy)
  - Run unit tests (pytest)
  - Build Docker image
  - Security scan (Trivy)
  - Post results to PR
```

### **4. Review and Merge**

- Reviewer checks code quality
- CI must pass (green checkmark)
- Approve and merge to `main`

### **5. Auto-Deploy to Dev**

```yaml
# .github/workflows/cd-dev.yml
on:
  push:
    branches: [main]

jobs:
  - Deploy to dev namespace in K8s
  - Run smoke tests
  - Verify health checks
```

### **6. Manual Promotion to Staging**

```bash
# Via GitHub Actions UI
# Workflow: cd-staging.yml
# Input: Commit SHA or tag
# Action: Deploy to staging namespace
```

### **7. Manual Promotion to Production**

```bash
# Via GitHub Actions UI
# Workflow: cd-production.yml
# Requires: Manual approval
# Action: Deploy to prod namespace
```

---

## Document Upload Workflow

### **Same PR Process**

Documents added to `data/documents/` follow the same PR-based workflow:

```bash
# Create branch for document upload
git checkout -b docs/add-q1-reports

# Add documents
git add data/documents/q1-sales.pdf
git add data/documents/q1-marketing.pdf
git commit -m "Add Q1 2026 reports"
git push origin docs/add-q1-reports

# Create PR → Review → Merge
```

### **After Merge to Main**

```yaml
# .github/workflows/data-sync.yml
on:
  push:
    branches: [main]
    paths:
      - 'data/documents/**'

jobs:
  - Upload documents to S3
  - Generate embeddings (Titan V2)
  - Update vector database
  - Notify completion
```

---

## Deployment Flow

```
Feature Branch
    ↓
  Pull Request (CI runs)
    ↓
  Code Review + Approval
    ↓
  Merge to main
    ↓
  Auto-deploy to dev namespace
    ↓
  Manual trigger → staging namespace
    ↓
  Manual trigger + approval → prod namespace
```

---

## Branch Protection Rules

### **`main` Branch Protection:**

```yaml
Settings → Branches → Branch protection rules → main

Required:
  ✅ Require pull request before merging
  ✅ Require approvals: 1
  ✅ Dismiss stale reviews when new commits are pushed
  ✅ Require status checks to pass before merging
     - ci.yml (build and test)
  ✅ Require conversation resolution before merging
  ✅ Do not allow bypassing the above settings

Optional:
  ⬜ Require signed commits
  ⬜ Require linear history
```

---

## Workflow Triggers

### **CI Workflow (`ci.yml`)**

**Triggers:**
- Pull requests to `main`
- Pushes to `main` (for verification)

**Actions:**
- Lint, test, build, scan
- Post results to PR

### **CD-Dev Workflow (`cd-dev.yml`)**

**Triggers:**
- Push to `main` (after PR merge)

**Actions:**
- Deploy to dev namespace
- Run smoke tests

### **CD-Staging Workflow (`cd-staging.yml`)**

**Triggers:**
- Manual (`workflow_dispatch`)

**Actions:**
- Deploy to staging namespace
- Run integration tests

### **CD-Production Workflow (`cd-production.yml`)**

**Triggers:**
- Manual (`workflow_dispatch`)
- Requires approval via GitHub Environments

**Actions:**
- Deploy to prod namespace
- Monitor for errors
- Auto-rollback if issues

### **Data Sync Workflow (`data-sync.yml`)**

**Triggers:**
- Push to `main` with changes in `data/documents/**`

**Actions:**
- Upload to S3
- Generate embeddings
- Update vector DB

### **Infrastructure Workflow (`infrastructure.yml`)**

**Triggers:**
- Push to `main` with changes in `terraform/**`
- Manual (`workflow_dispatch`)

**Actions:**
- Terraform plan
- Terraform apply (with approval)

---

## Example Scenarios

### **Scenario 1: Add New Feature**

```bash
# Day 1: Start feature
git checkout -b feature/intelligent-routing
# Code changes
git push origin feature/intelligent-routing
# Create PR

# Day 2: Address review comments
git commit -m "Address review feedback"
git push origin feature/intelligent-routing

# Day 3: Merge
# PR approved → Merge to main → Auto-deploy to dev
```

### **Scenario 2: Add Documents**

```bash
# Admin adds company policies
git checkout -b docs/add-hr-policies
git add data/documents/hr-policy-2026.pdf
git commit -m "Add 2026 HR policies"
git push origin docs/add-hr-policies
# Create PR → Quick review → Merge → Auto-processed
```

### **Scenario 3: Hotfix**

```bash
# Critical bug found in production
git checkout -b hotfix/fix-cache-bug
# Fix bug
git commit -m "Fix Redis cache invalidation bug"
git push origin hotfix/fix-cache-bug
# Create PR → Expedited review → Merge → Deploy to dev → staging → prod
```

---

## Benefits of This Approach

✅ **Simple** - Only one long-lived branch  
✅ **Safe** - All changes reviewed via PR  
✅ **Consistent** - Same process for code and data  
✅ **Industry Standard** - GitHub Flow (used by GitHub, Shopify, etc.)  
✅ **Fast** - No waiting for release cycles  
✅ **Auditable** - Full Git history of all changes  
✅ **Reversible** - Easy to revert bad changes  

---

## Best Practices

1. **Keep branches short-lived** - Merge within 1-3 days
2. **Small, focused PRs** - Easier to review
3. **Descriptive branch names** - `feature/add-redis-caching` not `fix-stuff`
4. **Meaningful commit messages** - Explain why, not just what
5. **Delete merged branches** - Keep repo clean
6. **Test locally first** - Don't rely on CI to catch basic errors
7. **Review your own PR** - Check the diff before requesting review

---

## References

- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub Actions Workflows](https://docs.github.com/en/actions/using-workflows)
