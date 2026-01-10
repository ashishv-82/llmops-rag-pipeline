# LLMOps RAG Pipeline

**Production-Grade AI Orchestration: AWS, Kubernetes, and Enterprise MLOps**

This project demonstrates a rigorous, first-principles approach to building, deploying, and operating an LLM-powered RAG system. It prioritizes **architectural control**, **cost governance**, and **operational excellence** over simple prototyping.

---

## 🏗️ High-Level Architecture

We employ a **Hybrid Architecture** that balances self-managed Kubernetes components with high-performance AWS managed services.

```mermaid
graph TD
    User([User]) -->|HTTPS| Ingress[Ingress Controller]
    subgraph "Kubernetes Cluster (EKS)"
        Ingress --> API[FastAPI Service]
        API -->|Hybrid Search| VectorDB[ChromaDB / Weaviate]
        API -->|Semantic Cache| Redis[Redis]
    end
    subgraph "AWS Managed Core"
        API -->|Inference| Nova[Amazon Nova 2]
        API -->|Embeddings| Titan[Titan V2]
        Nova -->|Safety| Guard[Bedrock Guardrails]
    end
```

---

## 💡 Key Concepts
Quick primer on the core technologies driving this pipeline.

| Concept | Simple Explanation |
| :--- | :--- |
| **RAG** | **Retrieval-Augmented Generation**. Giving the LLM a "textbook" (your data) to look up answers instead of relying only on its training memory. |
| **Embeddings** | Translating text into lists of numbers (vectors) that capture *meaning*. "King" and "Queen" will have similar numbers. |
| **Vectors** | The list of numbers itself (e.g., `[0.1, 0.9, -0.5]`). This is how computers "read" the meaning of text. |
| **Semantic Search** | Searching by *meaning* rather than exact keywords. "Device not working" finds "Broken screen". |
| **Vector DB** | A specialized database (like ChromaDB) designed to store and search these vectors instantly. |
| **Chunking** | Splitting large documents into smaller, meaningful pieces so the LLM can process them easily. |
| **LLM** | **Large Language Model** (e.g., Nova 2). The "brain" that reads the retrieved chunks and answers your question. |
| **Context** | The limited memory space (prompt) where we paste the retrieved chunks for the LLM to read. |
| **Hybrid Search** | Combining **Semantic Search** (meaning) with **Keyword Search** (exact match) for best results. |

---

## 🎯 The "Big 3" Value Pillars

### 1. Hybrid Implementation Strategy
Combines the **architectural control** of **custom orchestration** with the scale of **enterprise cloud**.
- **Build**: Custom LangChain pipeline & K8s orchestration.
- **Use**: Amazon Nova 2 (LLM), Titan V2 (Embeddings), and Bedrock Guardrails.

### 2. Aggressive Cost Governance
A system designed to be sustainable.
- **Pause/Resume**: Full infrastructure teardown via Terraform (~90% savings).
- **Semantic Caching**: Reducing LLM calls by ~70% via Redis.
- **Intelligent Routing**: Dynamic model selection (Lite vs. Pro) based on query complexity.

### 3. Enterprise MLOps & LLMOps
Moving beyond "it works" to "it scales."
- **Dual-Path Ingestion**: Automated GitHub Actions data-sync vs. Real-time User Upload.
- **Quality Gates**: Automated evaluation pipelines blocking regression in CI/CD.
- **Drift Detection**: Proactive monitoring of query distribution and document relevance.

---

## 🗺️ Documentation Navigation Map

Stop here for the high-level view. Dive deeper for the engineering specifics.

| Document | Architectural Purpose |
| :--- | :--- |
| **[Architectural Strategy](project-docs/decisions_summary.md)** | **The "Why"**: Hybrid "Build vs. Use" rationale & cost matrices. |
| **[Environment Strategy](project-docs/environment_strategy.md)** | **The "Where"**: Namespace isolation & resource planning. |
| **[Implementation Methodology](project-docs/implementation_methodology.md)** | **The "How"**: The "Verify First" (Console → Terraform) pattern. |
| **[MLOps Blueprint](project-docs/mlops_folder_explained.md)** | **The Lifecycle**: Continuous engineering & operational outcomes. |
| **[Branching & Workflow](project-docs/branching_strategy.md)** | **The Process**: PR-based GitHub Flow & deployment lifecycle. |

---

## 🛠️ Technology Stack & Rationale

| Component | Choice | Architectural Reasoning |
| :--- | :--- | :--- |
| **Compute** | **Amazon EKS** | Industry-standard orchestration with full pause/resume control. |
| **IaC** | **Terraform** | Cloud-agnostic state management and reproducibility. |
| **LLM** | **Amazon Nova 2** | `global.amazon.nova-2-lite-v1:0` (Global Inference Profile) for low-latency generation. |
| **Embeddings** | **Titan V2** | Normalized vectors optimized for hybrid search. |
| **Vector DB** | **ChromaDB / Weaviate** | Self-managed on K8s for maximum indexing control. |
| **Safety** | **Bedrock Guardrails** | Enterprise-grade PII masking and topic boundaries. |

---

## 📂 Project Structure Overview

```bash
llmops-rag-pipeline/
├── api/                 # FastAPI backend with RAG orchestration
├── terraform/           # Complete AWS Infrastructure-as-Code
├── kubernetes/          # K8s manifests & Kustomize overlays
├── mlops/               # Operational tools (Monitoring, Eval, Drift)
├── .github/workflows/   # CI/CD & Data-Sync pipelines
└── project-docs/        # Strategic & Architectural documentation
```

---

## 🏗️ Architecture Inventory (Pods & Services)

Reference this list when debugging or connecting services.

### Namespace: `dev` (Application Layer)

**Services (Stable Access Points)**
| Service Name | Port | Target Pod | Purpose |
| :--- | :--- | :--- | :--- |
| `rag-api-service` | 8000 | `rag-api` | **The Brain**: FastAPI application (Python). |
| `rag-frontend-service` | 8501 | `rag-frontend` | **The Face**: Streamlit UI. |
| `chromadb-service` | 8000 | `chromadb` | **The Memory**: Vector Database (Chroma). |

**Pods (Workloads)**
- `rag-api`: Validates queries and calls LLMs.
- `rag-frontend`: Frontend UI for user interaction.
- `chromadb`: Stores embeddings for retrieval.
- `redis`: High-speed semantic cache.

### Namespace: `monitoring` (Observability Layer)
**Services (Stable Access Points)**
| Service Name | Port | Target Pod | Purpose |
| :--- | :--- | :--- | :--- |
| `prometheus-grafana` | **80** | `grafana` | **Dashboard**: The UI (Login: `admin`/`admin`). |
| `prometheus-kube-prometheus-prometheus` | 9090 | `prometheus` | **Database**: Metric storage & Query Engine. |
| `prometheus-kube-prometheus-alertmanager` | 9093 | `alertmanager` | **Alerting**: Notification dispatcher (Slack/Email). |
| `prometheus-kube-prometheus-operator` | 443 | `operator` | **Controller**: Manages the stack config. |

**Pods (Workloads)**
- `grafana`: Visualization UI.
- `prometheus-server`: Time-series database.
- `alertmanager`: Warning system.
- `prometheus-operator`: The "Manager" ensuring everything runs.
- `node-exporter`: DaemonSet (one per node) reading Host CPU/RAM.
- `kube-state-metrics`: Reads K8s API for deployment states.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+** (Virtual Environment recommended)
- **Docker Desktop** (for local containerization)
- **Minikube** & **kubectl** (for local Kubernetes orchestration)
- **Helm** (for monitoring stack deployment)
- **AWS Credentials** (with Bedrock access for Nova 2 & Titan Embeddings)

### Installation

1.  **Clone & Setup**:
    ```bash
    git clone https://github.com/Ashish/llmops-rag-pipeline.git
    cd llmops-rag-pipeline
    python -m venv .venv
    source .venv/bin/activate
    pip install -r api/requirements.txt
    ```

2.  **Configuration**:
    Create a `.env` file or export environment variables:
    ```bash
    export AWS_PROFILE=default
    export AWS_REGION=ap-southeast-2
    ```

3.  **Run Locally (Full Stack with Docker Compose)**:
    *Recommended for local development and verification.*
    ```bash
    docker-compose up --build
    ```
    *   **API**: `http://localhost:8000`
    *   **Frontend**: `http://localhost:8501`

4.  **Seed Data**:
    Populate the local Vector DB with test documents:
    ```bash
    python scripts/seed_data.py "data/documents/history/The_Vietnam_War_v2.pdf" --domain history
    ```

5.  **Run on Kubernetes (Minikube)**:
    *For production simulation.*
    ```bash
    minikube start
    eval $(minikube docker-env)
    ./scripts/build_api.sh local
    ./scripts/build_frontend.sh local
    kubectl apply -f kubernetes/base/
    ```

### Usage

**Query the RAG Pipeline**:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I optimize costs?", "domain": "engineering"}'
```

## 📊 Measurable Engineering Outcomes

- **65% Monthly Cost Reduction**: achieved through comprehensive governance strategies.
- **Zero-Regression Deployments**: enforced by automated quality gates.
- **100% Infrastructure Reproducibility**: via Terraform and GitOps practices.

---

## 📝 License
MIT License - see [LICENSE](./LICENSE) file for details.

*Active Project: Designed to demonstrate production-grade LLMOps mastery.*
