# LLMOps RAG Pipeline - Project Tasks

## 📊 Progress Summary

**Overall Progress**: 120/298 tasks (40%)
 
 ```
 Planning & Documentation  ██████████ 100% (14/14)
 Phase 1: Foundation       ██████████ 100% (20/20)
 Phase 2: Kubernetes       ██████████ 100% (16/16)
 Phase 3: Core Features    ██████████ 100% (31/31)
 Phase 4: CI/CD            ██████████ 100% (39/39)
 Phase 5: Monitoring       ░░░░░░░░░░  0% (0/24)
 Phase 6: MLOps/LLMOps     ░░░░░░░░░░  0% (0/35)
 Phase 7: EKS Deployment   ░░░░░░░░░░  0% (0/41)
 Phase 8: Documentation    ░░░░░░░░░░  0% (0/47)
 Future Enhancements       ░░░░░░░░░░  0% (0/25)
 Ongoing Tasks             ░░░░░░░░░░  0% (0/6)
 ```

**Current Focus**: ✅ Phase 4 Complete → 🚀 Ready for Phase 5: Monitoring & Observability
**Last Updated**: 07 January, 2026

---

## Planning & Documentation
- [x] Define project concept and architecture
- [x] Determine cost optimization strategy (pause/resume)
- [x] Choose hybrid architecture approach
- [x] Finalize technology stack (Nova 2, Titan V2, Guardrails)
- [x] Update project proposal with all decisions
- [x] Create comprehensive README
- [x] Document architectural decisions
- [x] Document environment strategy (namespace-based)
- [x] Document branching strategy (PR-based GitHub Flow)
- [x] Add project structure to README
- [x] Document dual-path document ingestion
- [x] Create detailed Phase 1 implementation plan
- [x] Set up initial project structure (create folders)
- [x] Create .gitignore and configuration files

---

## Phase 1: Foundation (Phase Allocation)

### Local Development Environment
- [x] Install Docker and Docker Compose
- [x] Install minikube or kind for local K8s
- [x] Install kubectl and helm
- [x] Install Terraform
- [x] Set up Python 3.11+ virtual environment
- [x] Install AWS CLI and configure credentials

### Basic FastAPI Application
- [x] Create project structure (api/, tests/, project-docs/)
- [x] Set up dependencies (requirements.txt or pyproject.toml)
- [x] Implement health check endpoints
- [x] Create basic API routes (documents, query)
- [x] Write Dockerfile for application
- [x] Test locally with Docker

### AWS Prerequisites
- [x] Configure AWS CLI with credentials
- [x] Create S3 bucket for Terraform state
- [x] Set up IAM user/role for Terraform
- [x] Test AWS connectivity

### Terraform Initialization
- [x] Set up Terraform backend configuration (S3 state)
- [x] Bootstrap backend resources (run scripts/bootstrap-backend.sh)
- [x] Create S3 buckets module (documents, embeddings)
- [x] Initialize and validate Terraform

---

## Phase 2: Kubernetes Setup (Phase Allocation)

### Local Kubernetes
- [x] Set up local K8s cluster (minikube or kind)
- [x] Create K8s manifests for API service
  - [x] Deployment
  - [x] Service
  - [x] ConfigMap
  - [x] Secrets (placeholder)
- [x] Deploy to local cluster
- [x] Test API endpoints locally
- [x] Verify health checks and readiness probes

### Terraform EKS Preparation
- [x] Create VPC module
- [x] Set up basic security groups
- [x] Create EKS cluster Terraform module (don't apply yet)
- [x] Configure node groups
- [x] Set up IAM roles for service accounts
- [x] Document EKS deployment plan for Phase 7
- [x] Set up kubectl context management

---

## Phase 3: Core Application Features (Phase Allocation)

### AWS Bedrock Integration
- [x] Set up AWS Bedrock access (IAM permissions)
- [x] Integrate Amazon Nova 2 Lite for LLM
- [x] Integrate Titan Embeddings V2 for embeddings
- [x] Configure Bedrock Guardrails
  - [x] PII masking (SSN, emails, phone numbers)
  - [x] Content filtering
  - [x] Topic boundaries
- [x] Test LLM and embedding generation

### Document Processing (Dual Path)
- [x] **Path 1: Web UI Upload**
  - [x] Implement file upload endpoint (FastAPI)
  - [x] Validate file types (PDF, TXT, DOCX)
  - [x] Upload to S3
  - [x] Trigger embedding generation

- [x] Implement document parsing (PDF, TXT)
- [x] Implement document chunking strategy

### Vector Database
- [x] Choose vector DB (ChromaDB or Weaviate)
- [x] Deploy vector DB on local K8s
- [x] Implement embedding storage
- [x] Implement vector retrieval
- [x] **Implement hybrid search (vector + keyword/BM25)**
  - [x] Vector similarity search
  - [x] Keyword matching (BM25)
  - [x] Combine scores with weights

### RAG Pipeline (LangChain)
- [x] Implement query processing
- [x] Implement context retrieval from vector DB
- [x] Implement prompt construction
- [x] Implement response generation with Nova 2
- [x] Add error handling and retries



### Simple Frontend
- [x] Create document upload UI
- [x] Display responses with sources
- [x] Add loading states and error handling

---

## Phase 4: CI/CD Pipeline (Phase Allocation)

### GitHub Actions - CI (Code)
- [x] Create `ci.yml` workflow
  - [x] Trigger on pull requests to main
  - [x] Set up linting (pylint, black, mypy)
  - [x] Set up unit tests (pytest)
  - [x] Configure Docker build
  - [x] Push Docker images to ECR
  - [x] Add security scanning (Trivy)
  - [x] Post results to PR

### GitHub Actions - Data Sync
### GitHub Actions - Data Sync
- [x] Create `data-sync.yml` workflow
  - [x] Trigger on push to main with changes in `data/documents/**`
  - [x] Upload new documents to S3
  - [x] Generate embeddings for new documents
  - [x] Update vector database
  - [x] Add validation and error handling

### GitHub Actions - CD Workflows
- [x] Create `cd-dev.yml` workflow
  - [x] Trigger on push to main (via `main.yml` orchestrator)
  - [x] Deploy to dev namespace in K8s (Simulated)
  - [x] Run smoke tests (Simulated)
  - [x] Verify health checks
- [x] Create `cd-staging.yml` workflow
  - [x] Trigger on manual dispatch
  - [x] Deploy to staging namespace in K8s
  - [x] Run integration tests
  - [x] Health check validation
- [x] Create `cd-production.yml` workflow
  - [x] Trigger on manual dispatch
  - [x] Require manual approval (GitHub Environments)
  - [x] Deploy to prod namespace in K8s
  - [x] Blue-green or canary deployment
  - [x] Automated rollback on failure

### GitHub Actions - Infrastructure
- [x] Create `infrastructure.yml` workflow
  - [x] Trigger on changes to `terraform/**` or manual dispatch
  - [x] Run terraform plan
  - [x] Run terraform apply (with approval)

### Branch Protection
- [x] Configure main branch protection
  - [x] Require pull request before merging
  - [x] Require 1 approval
  - [x] Require CI to pass
  - [x] Require conversation resolution

---

## Phase 5: Monitoring & Observability (Phase Allocation)

### Prometheus & Grafana (Terraform/Helm)
- [x] Create `monitoring` Terraform module
- [x] Deploy `kube-prometheus-stack` via Helm
- [x] Configure Grafana dashboards via Helm values
- [x] Verify Prometheus scraping

### Application Instrumentation
- [x] Add `prometheus-fastapi-instrumentator` library
- [x] Define custom metrics (Cost, Tokens, Latency) in `api/utils/metrics.py`
- [x] Expose `/metrics` endpoint
- [x] Create ServiceMonitor for Prometheus scraping
- [ ] Integrate cost tracking in RAG service
- [ ] Integrate token tracking in RAG service
- [ ] Integrate latency tracking in query endpoint
- [ ] Test metrics with real API requests

### Cost Tracking Dashboard (Grafana)
- [ ] Create cost per query visualization
- [ ] Create cost per service breakdown
- [ ] Create daily/weekly/monthly cost trends
- [ ] Create LLM token usage tracking
- [ ] Create cost breakdown by model (Nova 2 Lite vs Pro)

### CloudWatch Integration
- [ ] Set up CloudWatch log aggregation
- [ ] Create custom CloudWatch metrics
- [ ] Configure log retention policies

### Alerting
- [ ] Set up cost anomaly detection alerts
- [ ] Set up budget threshold alerts
- [ ] Set up error rate alerts
- [ ] Set up performance degradation alerts
- [ ] Configure notification channels (SNS/email)

### Distributed Tracing
- [ ] Add Jaeger or AWS X-Ray
- [ ] Instrument API calls
- [ ] Trace LLM requests

---

## Phase 6: MLOps/LLMOps Features (Phase Allocation)

### Semantic Caching (Redis)
- [ ] Deploy Redis on K8s
- [ ] Implement embedding caching
- [ ] Implement LLM response caching
- [ ] Implement similarity-based cache lookup
- [ ] Configure TTL and cache invalidation
- [ ] Track cache hit rate metrics

### Intelligent LLM Routing
- [ ] Implement query complexity analysis
- [ ] Route simple queries to Nova 2 Lite
- [ ] Route complex queries to Nova 2 Pro
- [ ] **Add domain-based routing logic**
  - [ ] Route by domain + complexity
  - [ ] Legal + complex → Nova 2 Pro
  - [ ] HR + simple → Nova 2 Lite
- [ ] Track cost savings from routing
- [ ] A/B test routing strategies

### Prompt Versioning
- [ ] Implement prompt version control
- [ ] Track token usage per prompt version
- [ ] A/B test different prompt strategies
- [ ] Measure quality vs. cost trade-offs

### MLflow Setup
- [ ] Deploy MLflow on K8s or use managed service
- [ ] Configure experiment tracking
- [ ] Set up model registry
- [ ] Track prompt versions

### Model Evaluation Pipeline
- [ ] Create automated response testing
- [ ] Implement quality metrics (relevance, accuracy, coherence)
- [ ] Track cost per evaluation run
- [ ] Measure latency
- [ ] Create evaluation reports

### A/B Testing Framework
- [ ] Implement framework for comparing models
- [ ] Implement framework for comparing prompts
- [ ] Measure quality vs. cost trade-offs
- [ ] Create A/B test reports

### Data Drift Detection
- [ ] Monitor query patterns over time
- [ ] Detect distribution shifts
- [ ] Alert on significant drift

---

## Phase 7: EKS Deployment & Infrastructure Optimization (Phase Allocation)

### EKS Deployment
- [ ] Apply Terraform configuration for EKS
- [ ] Deploy all Kubernetes resources to EKS
- [ ] Configure ingress and load balancers
- [ ] Verify all services are running
- [ ] Test end-to-end functionality
- [ ] **Revert CD Simulation Mode**: Uncomment `kubectl` commands in `cd-dev.yml`
- [ ] **Enable Notifications**: Re-enable Slack webhook in `cd-dev.yml`

### S3 Lifecycle Policies
- [ ] Implement 30-day transition to Standard-IA
- [ ] Implement 90-day transition to Glacier
- [ ] Document cost savings
- [ ] Monitor storage costs

### Time-Based Auto-Scaling
- [ ] Implement off-hours scaling (scale down at night)
- [ ] Configure cost-aware HPA policies
- [ ] Document scaling behavior
- [ ] Test scaling triggers

### Resource Tagging
- [ ] Implement cost allocation tags (Project, Environment, CostCenter)
- [ ] Add ownership and management tags
- [ ] Enable cost attribution in AWS Cost Explorer
- [ ] Verify tags in AWS console

### **Pause/Resume Validation (CRITICAL)**
- [ ] Create one-click pause/resume master script (`pause_resume.sh`)
- [ ] Test `terraform destroy` (full teardown)
- [ ] Verify data persistence (S3, ECR, Secrets Manager)
- [ ] Test `terraform apply` (full restoration)
- [ ] Document recovery time (~20 minutes)
- [ ] Verify application functionality after restore
- [ ] Test multiple destroy/apply cycles
- [ ] Document any issues and fixes

### Security & Authentication
- [ ] **Infrastructure Secrets**
  - [ ] Create `rag-api-secrets` in AWS Secrets Manager (Console)
  - [ ] Install External Secrets Operator (ESO) on EKS
  - [ ] Create `SecretStore` and `ExternalSecret` manifests
- [ ] Add rate limiting
- [ ] Implement authentication (API keys or OAuth)
- [ ] Configure network policies in K8s
- [ ] Implement pod security policies
- [ ] Validate IAM least-privilege access
- [ ] Test secrets rotation

### Backup & Disaster Recovery
- [ ] Validate S3 versioning
- [ ] Test ECR image backup
- [ ] Create RDS snapshots (if using)
- [ ] Document recovery procedures
- [ ] Test restore procedures

---

## Phase 8: Documentation & Portfolio Polish (Week 8)

### README
- [ ] Write project overview and features
- [ ] Document architecture decisions with rationale
- [ ] Create quick start guide
- [ ] List technology stack
- [ ] Add badges (build status, license, etc.)

### Architecture Diagrams
- [ ] Create high-level system architecture diagram
- [ ] Create data flow diagram
- [ ] Create cost optimization flow diagram
- [ ] Create pause/resume workflow diagram
- [ ] Add diagrams to documentation

### **Cost Optimization Report (CRITICAL)**
- [ ] Document baseline costs (naive implementation)
- [ ] Document optimized costs (with all strategies)
- [ ] Create breakdown of savings by strategy:
  - [ ] Semantic caching: X% reduction
  - [ ] Intelligent routing: Y% reduction
  - [ ] Pause/resume: Z% reduction
  - [ ] S3 lifecycle: W% reduction
- [ ] Create ROI analysis with graphs
- [ ] Create before/after cost comparison
- [ ] Add real metrics from CloudWatch/Cost Explorer

### Pause/Resume Documentation
- [ ] Write step-by-step guide (destroy/apply)
- [ ] Document cost implications
- [ ] Document recovery procedures
- [ ] Create troubleshooting guide
- [ ] Add screenshots or recordings

### Architecture Decision Records (ADRs)
- [ ] Document why hybrid approach
- [ ] Document technology choices (self-managed vs managed)
- [ ] Document trade-offs and rationale
- [ ] Create ADR template for future decisions

### Deployment Procedures
- [ ] Document local development setup
- [ ] Document AWS deployment steps
- [ ] Document environment configuration
- [ ] Create deployment checklist

### Runbooks
- [ ] Create scaling procedures runbook
- [ ] Create incident response runbook
- [ ] Create cost monitoring runbook
- [ ] Create backup/restore runbook

### Demo Materials
- [ ] Record demo video
  - [ ] System walkthrough
  - [ ] Cost optimization demonstration
  - [ ] Pause/resume in action
- [ ] Create slide deck (optional)
- [ ] Prepare Architectural Rationale

### Blog Post (Optional)
- [ ] Write technical deep-dive
- [ ] Explain cost optimization strategies
- [ ] Share lessons learned
- [ ] Publish on Medium/Dev.to

---

## Ongoing Tasks
- [ ] Track costs daily in AWS Cost Explorer
- [ ] Update documentation as features are added
- [ ] Refactor and optimize code regularly
- [ ] Apply security updates
- [ ] Monitor system performance
- [ ] Review and update cost optimization strategies

---

## Future Enhancements (Deferred)

### Domain-Specific Features
- [ ] **Metadata Tagging System**
  - [ ] Define metadata schema (domain, department, doc_type, tags)
  - [ ] Implement auto-tagging during document upload
  - [ ] Store metadata in vector DB
  - [ ] Create metadata validation
- [ ] **Domain Filtering**
  - [ ] Implement domain filter in query API
  - [ ] Add domain-based vector DB filtering
  - [ ] Create multi-domain query support
  - [ ] Test filtering accuracy
- [ ] **Domain-Aware Prompts**
  - [ ] Create prompt templates per domain (Legal, HR, Marketing, Engineering)
  - [ ] Implement prompt selection logic
  - [ ] Test domain-specific response quality
- [ ] **Access Control (Optional)**
  - [ ] Implement role-based domain access
  - [ ] Add domain permissions to user model
  - [ ] Test access restrictions
- [ ] **Analytics**
  - [ ] Track queries by domain
  - [ ] Measure accuracy by domain
  - [ ] Create domain usage dashboard

### Advanced Frontend
- [ ] Add domain filter dropdown
- [ ] Implement chat history
- [ ] Add user authentication UI
