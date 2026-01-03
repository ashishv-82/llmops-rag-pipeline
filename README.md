# LLMOps RAG Pipeline

**End-to-end RAG pipeline with MLOps best practices: AWS, Kubernetes, Terraform, and automated CI/CD**

## 🎯 Project Overview

An intelligent document Q&A platform built with a focus on **production-grade MLOps/LLMOps practices** and **cost optimization**. This project demonstrates the complete lifecycle of deploying and operating an LLM-powered application using industry-standard tools and cloud-native architecture.

### Key Features

- 🤖 **RAG-based Q&A** - Upload documents and ask questions using LLMs
- 💰 **Cost-Optimized** - Pause/resume architecture, intelligent caching, smart routing
- 🏗️ **Infrastructure as Code** - 100% Terraform-managed AWS infrastructure
- ☸️ **Kubernetes Native** - Deployed on EKS with auto-scaling and monitoring
- 🔄 **Complete CI/CD** - GitHub Actions for automated testing and deployment
- 📊 **Real-time Monitoring** - Prometheus, Grafana, and cost tracking dashboards
- 🔬 **MLOps Best Practices** - Experiment tracking, model versioning, A/B testing

## 💡 Why This Project?

This project showcases:

1. **Cost Optimization as a Feature** - Demonstrates 60%+ cost reduction through intelligent architecture
2. **Pause/Resume Infrastructure** - `terraform destroy` → $0/day, `terraform apply` → everything back in 20 minutes
3. **Production-Ready Patterns** - Stateless design, GitOps, comprehensive monitoring
4. **Real-World MLOps** - Not just ML models, but the complete operational infrastructure

## 🏗️ Architecture

**Pause/Resume Design Principles:**

✅ All data in S3 - Documents, embeddings, configurations persist  
✅ All images in ECR - Docker images survive infrastructure destruction  
✅ All infrastructure in Terraform - 100% reproducible  
✅ All K8s configs in code - GitOps approach  
✅ Secrets in AWS Secrets Manager - Persist independently  
✅ Stateless applications - No local state  

**Result:** Complete infrastructure teardown and recreation in ~20 minutes with zero manual effort.

## 🛠️ Tech Stack & Architecture Decisions

### **Hybrid Approach: Custom Pipeline + Latest AWS Services**

This project combines self-managed components (for maximum control and flexibility) with cutting-edge AWS managed services (for enterprise features).

---

### **Infrastructure**

| Component | Choice | Alternative Considered | Why This Choice |
|-----------|--------|----------------------|-----------------|
| **Compute** | Amazon EKS | ECS Fargate | ✅ Industry-standard Kubernetes<br>✅ Full orchestration control<br>✅ Optimal for pause/resume architecture |
| **IaC** | Terraform | CloudFormation | ✅ Cloud-agnostic skills<br>✅ Industry standard<br>✅ Better state management |
| **Container Registry** | Amazon ECR | Docker Hub | ✅ AWS-native integration<br>✅ Persists during pause/resume<br>✅ Private and secure |
| **Storage** | Amazon S3 | EBS/EFS | ✅ Serverless (no compute costs when paused)<br>✅ Lifecycle policies for cost optimization<br>✅ Durability and versioning |

---

### **LLM & Embeddings**

| Component | Choice | Alternative Considered | Why This Choice |
|-----------|--------|----------------------|-----------------|
| **LLM** | Amazon Nova 2 (Lite/Pro) | Claude 3 / GPT-4 | ✅ Latest 2026 model family<br>✅ Faster and cheaper<br>✅ AWS-native (lower latency)<br>✅ Bedrock Guardrails integration |
| **Embeddings** | Titan Embeddings V2 | Sentence Transformers | ✅ Normalized vectors (better accuracy)<br>✅ AWS-native (no external API)<br>✅ Optimized for hybrid search<br>✅ Cost-effective |
| **Orchestration** | Custom LangChain Pipeline | Bedrock Knowledge Bases | ✅ Full control over RAG logic<br>✅ Advanced MLOps capabilities<br>✅ Custom optimization opportunities<br>❌ More complex (trade-off for flexibility) |

---

### **Vector Database**

| Component | Choice | Alternative Considered | Why This Choice |
|-----------|--------|----------------------|-----------------|
| **Vector DB** | ChromaDB/Weaviate on K8s | OpenSearch Managed | ✅ Self-managed = maximum control<br>✅ Pause/resume friendly (no ongoing costs)<br>✅ Full control over hybrid search implementation<br>✅ Custom optimization capabilities<br>❌ More operational overhead (intentional trade-off) |

**Decision:** Self-managed vector DB on Kubernetes
- **Technical depth**: Full understanding of vector operations, indexing, and retrieval
- **Cost optimization**: Fits pause/resume architecture perfectly
- **Flexibility**: Enables hybrid search, custom ranking, and A/B testing

---

### **Application Stack**

- **Python 3.11+**: FastAPI for API layer, LangChain for RAG orchestration
- **FastAPI**: High-performance async API framework
- **LangChain**: Flexible LLM orchestration with full customization
- **Bedrock Guardrails**: PII masking, content filtering, topic control

---

### **Security & Enterprise Features**

| Feature | Implementation | Why Important |
|---------|---------------|---------------|
| **Guardrails** | AWS Bedrock Guardrails | ✅ PII masking (SSN, emails)<br>✅ Content filtering<br>✅ Topic boundaries<br>✅ Enterprise-grade safety |
| **Hybrid Search** | Vector + Keyword (BM25) | ✅ Semantic understanding + exact matching<br>✅ Better for part numbers, codes, names<br>✅ Production-grade accuracy |
| **IAM Roles** | Terraform-managed | ✅ Least-privilege access<br>✅ Service-to-service auth<br>✅ No hardcoded credentials |

---

### **MLOps & Monitoring**

- **MLflow**: Experiment tracking and model registry
- **Prometheus**: Metrics collection (custom LLM metrics)
- **Grafana**: Visualization dashboards (cost, performance, quality)
- **CloudWatch**: Centralized logging and AWS-native metrics
- **GitHub Actions**: CI/CD for code AND data pipelines

---

### **Document Ingestion (Dual Path)**

**Path 1: User Upload (Primary)**
- Web UI → FastAPI → S3 → Real-time embedding → Vector DB
- **Use case**: End users uploading their documents
- **Processing**: Real-time, on-demand

**Path 2: Automated Sync (DevOps)**
- GitHub → Actions → S3 → Batch embedding → Vector DB
- **Use case**: Bulk updates, sample data, official documentation
- **Processing**: Automated, scheduled or on-commit

**Why both?**
- ✅ Shows user-facing features (Path 1)
- ✅ Demonstrates DevOps automation (Path 2)
- ✅ Covers ad-hoc and batch processing patterns
- ✅ Real-world production pattern

---

### **Cost Optimization Strategy**

| Strategy | Implementation | Expected Savings |
|----------|---------------|------------------|
| **Pause/Resume** | Terraform destroy/apply | 90% of compute costs |
| **Semantic Caching** | Redis + similarity check | 70% reduction in LLM calls |
| **Intelligent Routing** | Route by query complexity | 60% reduction in LLM costs |
| **S3 Lifecycle** | Auto-archive to Glacier | 40% reduction in storage costs |
| **Time-based Scaling** | Auto-scale down off-hours | 45% reduction in compute costs |

## 💰 Cost Structure

**Development Phase** (Weeks 1-6): ~$30-40/month  
**EKS Deployment** (Weeks 7-8): ~$100 for 2 weeks  
**Maintenance**: ~$10-20/month (infrastructure destroyed, S3/ECR storage only)  

**Total Project Cost**: ~$195 over 8 weeks

**On-Demand Usage**: ~$3-4 per day when spun up for demos

---

## 🔬 LLMOps vs MLOps in This Project

This project demonstrates both **LLMOps** (LLM-specific operations) and **MLOps** (traditional ML operations).

### **LLMOps Components (25%)**

LLM-specific challenges and solutions:

- **Prompt Engineering** - Versioning, optimization, A/B testing
- **Token Management** - Track usage, calculate cost per query
- **Intelligent Routing** - Route queries to appropriate models (Nova 2 Lite vs Pro)
- **RAG Optimization** - Chunking strategy, hybrid search tuning, retrieval quality
- **LLM Evaluation** - Response quality, hallucination detection, safety guardrails
- **Cost Optimization** - Semantic caching, prompt efficiency, model selection

### **MLOps Components (25%)**

Traditional ML operations:

- **Infrastructure** - Kubernetes, Terraform, auto-scaling
- **CI/CD** - Automated testing, deployment pipelines, rollback
- **Monitoring** - Prometheus, Grafana, distributed tracing
- **Data Management** - Versioning, quality validation, drift detection
- **Experiment Tracking** - MLflow, A/B testing framework
- **Model Lifecycle** - Deployment, versioning, performance monitoring

### **Hybrid LLMOps + MLOps (50%)**

Where both domains intersect:

| Feature | MLOps Aspect | LLMOps Aspect |
|---------|-------------|---------------|
| **Cost Tracking** | Infrastructure monitoring | Token usage, cost per query |
| **Caching** | Standard caching patterns | Semantic similarity matching |
| **Evaluation** | Metrics framework | LLM-specific quality measures |
| **A/B Testing** | Testing infrastructure | Prompt/model comparison |
| **Data Pipeline** | ETL processes | Document processing for RAG |

**Portfolio Value**: This project demonstrates expertise in both traditional MLOps and modern LLMOps, showing you understand the full spectrum of AI operations.

---

## 📋 Project Status

🚧 **In Planning Phase**

See [`project_proposal.md`](./project_proposal.md) for detailed project plan and implementation phases.

## 🚀 Quick Start

*Coming soon - project is in planning phase*

## 📚 Documentation

- [`project_proposal.md`](./project_proposal.md) - Detailed project proposal and architecture
- More documentation coming as project develops

## 🎯 Technical Capabilities

This project demonstrates hands-on experience with:

- ✅ AWS services (EKS, S3, IAM, CloudWatch, Bedrock)
- ✅ Terraform for infrastructure management
- ✅ Kubernetes deployment and operations
- ✅ LLMOps and MLOps practices
- ✅ CI/CD with GitHub Actions
- ✅ Cost optimization strategies
- ✅ Production monitoring and observability

## 📝 License

MIT License - see [LICENSE](./LICENSE) file for details

---

**Note**: This is an active project. The architecture and implementation are designed to showcase production-grade practices while maintaining cost efficiency.
