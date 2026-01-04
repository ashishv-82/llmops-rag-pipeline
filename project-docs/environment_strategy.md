# Environment Strategy: Single Cluster, Multiple Namespaces

This project uses a **Single EKS Cluster + Kubernetes Namespaces** to balance production-grade isolation with a strictly optimized cost profile.

---

## 🗺️ Shared Architecture (Phases 7-8)

By sharing the Control Plane, we achieve environment isolation without the overhead of multiple expensive EKS clusters.

```mermaid
graph TD
    subgraph "AWS Account (ap-southeast-2)"
        subgraph "Single EKS Cluster"
            subgraph "Namespace: dev"
                A1[API v1] --> B1[ChromaDB]
                C1[Redis Cache]
            end
            subgraph "Namespace: staging"
                A2[API v1-beta] --> B2[ChromaDB]
                C2[Redis Cache]
            end
            subgraph "Namespace: prod"
                A3[API v1-stable] --> B3[ChromaDB]
                C3[Redis Cache]
            end
        end
    end
```

---

## 📊 Cost-Isolation Matrix

The rationale behind our choosing "Single Cluster with Namespaces" for this portfolio project.

| Option | Cost (2 wks) | Isolation | Complexity | Decision |
| :--- | :--- | :--- | :--- | :--- |
| **Namespaces** | **~$100** | Logical (K8s) | Moderate | ✅ **Selected** |
| **Separate Clusters** | ~$350 | Physical (AWS) | High | ❌ Too Expensive |
| **Single Namespace** | ~$100 | None | Low | ❌ Unprofessional |

---

## 🛠️ Implementation Hierarchy

Detailed configurations for both Infrastructure-as-Code and Kubernetes orchestration.

<details>
<summary>▶️ <b>Terraform Environment Modules (Click to expand)</b></summary>

```
terraform/
├── modules/              # Reusable Blueprints (eks, vpc, s3, iam)
└── environments/
    ├── dev/              # ACTIVE: Defines the shared cluster
    │   ├── main.tf
    │   └── terraform.tfvars
    ├── staging/          # Portfolio Only: Overrides for staging logic
    └── prod/             # Portfolio Only: Overrides for production logic
```
</details>

<details>
<summary>▶️ <b>Kubernetes Kustomize Overlays (Click to expand)</b></summary>

```
kubernetes/
├── base/                 # Standard Deployments/Services
└── overlays/             # Environment-specific overrides
    ├── dev/              # Resource limits: 256Mi, 1 Replica
    ├── staging/          # Resource limits: 512Mi, 2 Replicas
    └── prod/             # Resource limits: 1Gi, 3 Replicas
```
</details>

---

## 💡 Interview Readiness: The "Why"

> [!IMPORTANT]
> **Talking Point:** "I chose a namespace-based strategy because it demonstrates **Pragmatic Engineering.** 
> - **Cost Awareness:** Saves 70% in cloud overhead while maintaining environment parity.
> - **K8s Mastery:** Proves competence in Namespace isolation, Resource Quotas, and Kustomize overlays.
> - **Growth Path:** The Terraform structure is designed for 'Lazy Scaling'—we can move to separate clusters in the future just by applying our existing staging/prod modules.

---

## 📉 Configuration Differences

| Feature | `dev` | `staging` | `prod` |
| :--- | :--- | :--- | :--- |
| **Log Level** | DEBUG | INFO | WARN |
| **Auto-scaling** | Disabled | 2-3 Replicas | 3-5 Replicas |
| **Persistence** | Instant | 15 min Sync | Real-time |

---

## 🎯 Summary
- **Strategy:** Logical isolation via K8s Namespaces.
- **Goal:** Production-grade simulation on a startup budget.
- **Value:** Shows you can make architecturally sound, cost-conscious infrastructure decisions.
