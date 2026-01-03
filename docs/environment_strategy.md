# Environment Strategy

## Decision: Namespace-Based Multi-Environment

---

## Overview

This project uses a **single EKS cluster with Kubernetes namespaces** for environment separation, rather than multiple separate AWS environments.

---

## Architecture

### **Local Development (Phases 1-6)**
```
Local Machine
└── Minikube/Kind Cluster
    └── Namespace: default
        ├── API
        ├── Vector DB
        ├── Redis
        └── Monitoring
```

**Cost**: $0 (runs on your laptop)

### **AWS Deployment (Phases 7-8)**
```
AWS Account
└── Single EKS Cluster
    ├── Namespace: dev
    │   ├── API (dev version)
    │   ├── Vector DB
    │   └── Redis
    ├── Namespace: staging
    │   ├── API (staging version)
    │   ├── Vector DB
    │   └── Redis
    └── Namespace: prod
        ├── API (production version)
        ├── Vector DB
        └── Redis
```

**Cost**: ~$100 for 2 weeks (single EKS cluster)

---

## Rationale

### **Why Single Cluster with Namespaces?**

✅ **Cost-Effective**
- Only one EKS control plane (~$73/month)
- Shared node pools across environments
- Total cost: ~$100 for 2 weeks vs. ~$300+ for 3 separate clusters

✅ **Portfolio-Worthy**
- Demonstrates understanding of multi-environment concepts
- Shows Kubernetes namespace isolation
- Proves you can design cost-effective architectures

✅ **Practical**
- How many small teams and startups actually do it
- Realistic for resource-constrained scenarios
- Interview-ready explanation

✅ **Best Practice Structure**
- Terraform organized by environment (dev/staging/prod folders)
- Kubernetes overlays for environment-specific configs
- CI/CD pipelines for each environment

---

## Implementation Details

### **1. Terraform Structure**

```
terraform/
├── modules/              # Reusable modules
│   ├── eks/
│   ├── vpc/
│   ├── s3/
│   └── iam/
└── environments/
    ├── dev/              # Only this will be applied
    │   ├── main.tf
    │   ├── variables.tf
    │   └── terraform.tfvars
    ├── staging/          # Structure only (for portfolio)
    │   └── main.tf
    └── prod/             # Structure only (for portfolio)
        └── main.tf
```

**What you'll actually deploy:**
```bash
cd terraform/environments/dev
terraform init
terraform apply  # Creates single EKS cluster
```

### **2. Kubernetes Structure**

```
kubernetes/
├── base/                 # Base configurations
│   ├── api-deployment.yaml
│   ├── vectordb-deployment.yaml
│   ├── redis-deployment.yaml
│   └── monitoring-stack.yaml
└── overlays/             # Environment-specific overrides
    ├── dev/
    │   └── kustomization.yaml
    ├── staging/
    │   └── kustomization.yaml
    └── prod/
        └── kustomization.yaml
```

**Deploy to different namespaces:**
```bash
# Create namespaces
kubectl create namespace dev
kubectl create namespace staging
kubectl create namespace prod

# Deploy to dev
kubectl apply -k kubernetes/overlays/dev -n dev

# Deploy to staging
kubectl apply -k kubernetes/overlays/staging -n staging

# Deploy to prod
kubectl apply -k kubernetes/overlays/prod -n prod
```

### **3. CI/CD Strategy**

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches:
      - develop    # → dev namespace
      - main       # → staging namespace
      - release    # → prod namespace

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/develop" ]]; then
            echo "namespace=dev" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "namespace=staging" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/release" ]]; then
            echo "namespace=prod" >> $GITHUB_OUTPUT
          fi
      
      - name: Deploy to K8s
        run: |
          kubectl apply -k kubernetes/overlays/${{ steps.env.outputs.namespace }} \
            -n ${{ steps.env.outputs.namespace }}
```

---

## Environment Differences

### **Resource Allocation**

| Environment | Replicas | CPU Request | Memory Request | Purpose |
|-------------|----------|-------------|----------------|---------|
| **dev** | 1 | 100m | 256Mi | Active development |
| **staging** | 2 | 200m | 512Mi | Pre-production testing |
| **prod** | 3 | 500m | 1Gi | Production workload |

### **Configuration Differences**

| Setting | dev | staging | prod |
|---------|-----|---------|------|
| **Log Level** | DEBUG | INFO | WARN |
| **Cache TTL** | 5 min | 15 min | 30 min |
| **Auto-scaling** | Disabled | Enabled (2-3) | Enabled (3-5) |
| **Monitoring** | Basic | Standard | Full |

---

## Alternative Considered

### **Option: Separate EKS Clusters**

```
AWS Account
├── EKS Cluster (dev) - $73/month
├── EKS Cluster (staging) - $73/month
└── EKS Cluster (prod) - $73/month
```

**Why NOT chosen:**
- ❌ **Cost**: ~$219/month (3x more expensive)
- ❌ **Overkill**: For a portfolio/learning project
- ❌ **Complexity**: More infrastructure to manage
- ❌ **Budget**: Exceeds $50/month target

**When to use separate clusters:**
- Large production systems
- Strict isolation requirements
- Different compliance needs per environment
- Large teams with dedicated environments

---

## Interview Talking Points

**Question**: "Why did you use namespaces instead of separate clusters?"

**Answer**: 
"I chose namespace-based separation for several reasons:

1. **Cost Efficiency**: Single EKS control plane saves ~$150/month while still demonstrating multi-environment concepts

2. **Realistic**: This mirrors how many startups and small teams actually operate - they use namespaces for environment separation until scale demands separate clusters

3. **Learning**: I wanted to demonstrate understanding of Kubernetes RBAC, network policies, and resource quotas for namespace isolation

4. **Flexibility**: The Terraform structure supports easy migration to separate clusters if needed - just apply the staging/prod environment configs

5. **Best Practices**: I still followed GitOps, environment-specific configs, and proper CI/CD patterns"

---

## Migration Path (Future)

If you need to scale to separate clusters later:

```bash
# Already have the structure
cd terraform/environments/staging
terraform apply  # Creates staging cluster

cd terraform/environments/prod
terraform apply  # Creates prod cluster
```

The modular Terraform design makes this straightforward.

---

## Summary

**Decision**: Single EKS cluster with namespace-based environments  
**Cost**: ~$100 for 2 weeks (vs. ~$300+ for 3 clusters)  
**Benefit**: Demonstrates multi-env best practices while staying cost-effective  
**Portfolio Value**: Shows pragmatic architecture decisions and cost awareness
