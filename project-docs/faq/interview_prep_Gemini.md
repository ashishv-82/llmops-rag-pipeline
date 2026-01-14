# 🎓 LLMOps RAG Pipeline: Ultimate Interview Preparation Guide

**Project**: `llmops-rag-pipeline`
**Role Focus**: AI Engineer, LLMOps Engineer, Cloud Architect
**Tech Stack**: AWS (Nova 2, Titan V2), Kubernetes (EKS), Python (FastAPI), Terraform, LangChain, Prometheus/Grafana.

---

## 🏗️ Section 1: System Design & Architecture

### 1. Can you describe the high-level architecture of this project?
**Answer:**
This is a **Hybrid RAG Architecture** that balances self-managed control with managed service scalability. It runs on a single **Amazon EKS** cluster with namespace isolation (dev, staging, prod).
- **Control Plane**: A Python **FastAPI** application orchestrates the logic.
- **Data Plane (Self-Managed)**: We run **ChromaDB** for vector storage and **Redis** for semantic caching directly on Kubernetes to maintain architectural control and minimize costs.
- **Intelligence Plane (AWS Managed)**: We leverage AWS Bedrock for the heavy compute, using **Amazon Nova 2** for generation and **Titan Embeddings V2** for vectorization.

### 2. Why did you choose a "Hybrid" approach instead of fully managed (e.g., AWS Bedrock Knowledge Bases)?
**Answer:**
I chose a "First-Principles" hybrid approach to demonstrate deep engineering mastery. While fully managed services are easier, they obscure the internal mechanics of RAG (chunking, hybrid search algorithms, caching strategies). By managing the Vector DB (Chroma) and orchestration layer myself, I gained fine-grained control over indexing and implemented custom cost-optimization strategies like **Semantic Caching** and **Intelligent Routing**, which wouldn't be possible in a black-box service.

### 3. How do you handle cost governance in this architecture?
**Answer:**
Cost optimization isn't an afterthought; it's a "Value Pillar" of the architecture. I implemented a multi-layered strategy:
1.  **Semantic Caching (Redis)**: We cache ~70% of redundant queries. If a user asks a question similar (>0.95 cosine similarity) to a previous one, we return the cached answer immediately, saving LLM tokens and latency.
2.  **Intelligent Routing**: A routing service analyzes query complexity. Simple queries (e.g., "What is the holiday policy?") go to **Nova 2 Lite** (cheaper), while complex legal analysis goes to **Nova 2 Pro** (more capable).
3.  **Infrastructure Pause/Resume**: Using Terraform, I can destroy the entire expensive compute layer (EKS nodes) when not in use and restore it in minutes, saving ~90% on idle cloud costs.

### 4. Why FastAPI over Flask or Django?
**Answer:**
FastAPI is chosen for its native **asynchronous** support (`async/await`). RAG applications are heavily I/O bound—spending most of their time waiting for the Vector DB or the LLM API to respond. FastAPI allows the server to handle thousands of concurrent requests while waiting, whereas a synchronous framework like Flask would block the thread. Additionally, FastAPI's automatic data validation (Pydantic) and built-in Swagger UI documentation drastically improve developer velocity and type safety.

### 5. Explain your "Dual-Path" Ingestion Strategy.
**Answer:**
I treat data ingestion both as a user action and a DevOps process:
1.  **User Path (Real-time)**: Users can upload documents via the Streamlit UI/API. These are processed immediately in background tasks.
2.  **DevOps Path (Data-as-Code)**: I have a dedicated GitHub Action (`data-sync.yml`). When I commit a PDF to the `data/documents/` folder in the repo, the CI/CD pipeline automatically detects the change, uploads it to S3, and triggers the embedding job. This ensures zero drift between the repository "truth" and the production vector database.

### 6. Strategy for environment isolation?
**Answer:**
To simulate a production environment on a budget, I used **Namespace Isolation** within a single EKS cluster rather than multiple clusters.
- **`dev`**: Debug logs, low resource quotas, unstable features.
- **`staging`**: Mirrors production settings, used for final verification.
- **`prod`**: High resource guarantees, requiring manual approval to deploy.
This saves ~70% of infrastructure costs (shared Control Plane) while proving I understand Kubernetes multi-tenancy rules.

### 7. Why Amazon Nova 2 instead of GPT-4 or Claude 3?
**Answer:**
Amazon Nova 2 is AWS's latest (2026) state-of-the-art model. I selected it for:
1.  **Performance/Cost Ratio**: Nova 2 Lite offers near-instant latency for simple queries at a fraction of the cost of GPT-4.
2.  **Native Integration**: As it's first-party AWS, it has lower latency within the VPC and better integration with Bedrock Guardrails compared to third-party models on Bedrock.

### 8. How does the system handle rapid scaling or traffic spikes?
**Answer:**
The system scales at two levels:
1.  **Pod Scaling**: The FastAPI deployment is configured with a Horizontal Pod Autoscaler (HPA), scaling replicas based on CPU/Memory usage.
2.  **Node Scaling**: The EKS Cluster Autoscaler creates new EC2 nodes if the pods can't fit on existing nodes.
Additionally, the asynchronous architecture ensures that even a single pod can handle a high throughput of concurrent requests without locking up.

---

## 🧠 Section 2: RAG & AI Fundamentals

### 9. Explain "Hybrid Search" and why you used it.
**Answer:**
Hybrid Search combines **Semantic Search** (Vector Similarity) with **Keyword Search** (BM25).
- **Vectors** are great for grasping *concepts* (e.g., "device malfunction" finds "broken screen").
- **Keywords** are critical for *exact matches* (e.g., finding a specific error code "ERR-505").
My system performs both searches and calculates a weighted score (alpha=0.7 for vectors). This prevents the common failure mode where semantic search misses exact technical terms or product names.

### 10. How do you chunk documents, and why does it matter?
**Answer:**
I use a recursive character splitter. Chunking is the single most critical factor in retrieval quality.
- If chunks are **too small**, the LLM lacks context (it sees a sentence, but not the paragraph).
- If chunks are **too large**, we dilute the vector meaning (averaging "King" and "Peasant" into a generic "Male"), and we waste the limited context window.
I specifically include a "chunk index" metadata field to allow the system to potentially fetch adjacent chunks if more context is needed.

### 11. What embedding model are you using and why?
**Answer:**
I use **Amazon Titan Embeddings V2**. It is optimized for RAG and supports variable dimensions, though I stick to 1024 or 512 for balance. Crucially, Titan V2 vectors are **normalized**, meaning their magnitude is 1. This optimizes the vector database performance as we can use Dot Product (faster) instead of Cosine Similarity (mathematically equivalent for normalized vectors).

### 12. How does the intelligent routing logic actually work?
**Answer:**
The `RoutingService` uses a rule-based complexity analyzer (built with NLTK).
- It counts tokens, sentences, and technical terms.
- It is domain-aware: A "Legal" query defaults to **Pro** unless very short, while an "HR" query defaults to **Lite**.
- It checks for logical operators ("if", "when", "unless") which imply complex reasoning is required.
This logic runs *before* the LLM call, acting as a traffic controller to direct the query to the most cost-effective model that can handle it.

### 13. What is "Semantic Caching"?
**Answer:**
Traditional caching works on exact key matches (URL A = Response A). In AI, users ask the same question in different ways ("How do I optimize cost?" vs "Cost optimization tips").
Semantic Caching turns the *question* into a vector. If the vector is extremely close (e.g., >0.95 similarity) to a cached question vector, we serve the cached answer. This is implemented using **Redis** and provides massive speedups and cost savings.

### 14. How do you handle "Hallucinations"?
**Answer:**
I use a multi-pronged approach:
1.  **Grounding**: The system prompt explicitly instructs Nova 2: "Answer ONLY using the provided context. If the answer is not there, say you don't know."
2.  **Evaluation**: An automated evaluation pipeline (using Nova 2 Pro as a judge) checks every answer for "Faithfulness" (is it supported by the context?).
3.  **Guardrails**: Bedrock Guardrails acts as a final filter to block off-topic or unsafe responses.

### 15. What are Bedrock Guardrails?
**Answer:**
Bedrock Guardrails is a safety layer that sits *outside* the model prompt. Even if the model tries to answer a malicious question, the Guardrail intercepts the output. In my project, I configured it to:
- Mask PII (Personal Identifiable Information) like emails and SSNs.
- Block specific topics not relevant to the business using "Topic Boundaries".
- Filter harmful content.

### 16. Why use standard Python `nltk` for routing instead of a small BERT model?
**Answer:**
Latency and overhead. The router runs on *every single request*. Loading even a small BERT model adds 50-100ms of latency and requires more RAM. The rule-based approach (counting words, detecting keywords) executes in microseconds (O(1)) and covers 80% of the complexity signals we care about. For this use case, simple heuristics beat complex ML.

---

## 🛠️ Section 3: Kubernetes & Infrastructure

### 17. Explain your decision to use Prometheus Operator vs standard Prometheus.
**Answer:**
I use the **Prometheus Operator** (via `kube-prometheus-stack`) because it allows "Monitoring as Code". Instead of manually editing a massive `prometheus.yaml` config and restarting the server, I define a Kubernetes Custom Resource called `ServiceMonitor`. The Operator watches for these resources and automatically hot-reloads the Prometheus config. It makes adding metrics for a new microservice as easy as deploying a single YAML file.

### 18. What are Liveness and Readiness probes?
**Answer:**
They are the heartbeat mechanisms for Kubernetes:
- **Liveness Probe**: Asks "Are you dead?". If this fails (e.g., deadlock), K8s restarts the pod.
- **Readiness Probe**: Asks "Are you busy?". If this fails (e.g., waiting for Redis connection), K8s stops sending user traffic to the pod but lets it keep running.
I implemented distinct endpoints (`/health/live`, `/health/ready`) in FastAPI to handle these scenarios correctly.

### 19. How is persistent storage handled for the Vector DB?
**Answer:**
Since ChromaDB is running in Kubernetes, it needs persistent storage or data is lost on restart. I used a **StatefulSet** (or Deployment with PVC) backed by an **AWS EBS Volume** via the CSI driver. This ensures that even if the ChromaDB pod crashes and moves to a different node, its "brain" (the vector index on the disk) follows it.

### 20. What is the role of the ServiceAccount in EKS?
**Answer:**
I use **IRSA** (IAM Roles for Service Accounts). Instead of giving the EC2 node broad permissions (insecure), I map a specific Kubernetes ServiceAccount (`rag-api-sa`) to a specific AWS IAM Role. This means *only* the API pod can access Bedrock and S3. Even if another pod on the same node is compromised, it cannot access those services. This is the principle of Least Privilege.

### 21. How do you safely expose the application to the internet?
**Answer:**
I use an **Ingress Controller** (AWS Load Balancer Controller). It provisions an Application Load Balancer (ALB) that terminates SSL/TLS and routes traffic to the internal Kubernetes Service. This provides a single, secure entry point and allows for features like WAF (Web Application Firewall) integration and path-based routing.

### 22. Why Terraform over CloudFormation?
**Answer:**
Terraform is cloud-agnostic and uses a state file (`.tfstate`) to track the "truth" of the infrastructure. Its syntax (HCL) is more readable than JSON/YAML, and its ecosystem of Modules allows me to reuse code. For example, I used the community `vpc` module to provision a best-practice network in 10 lines of code, rather than writing 200 lines of CloudFormation.

### 23. What happens when you run `terraform destroy`?
**Answer:**
This is part of my "Pause/Resume" strategy. It tears down the EKS cluster, Load Balancers, and Nodes to stop the billing meter. However, I explicitly use **S3 Backends** for Terraform state and prevent the destruction of "Data" resources (S3 buckets containing documents, EBS volumes snapshots) using lifecycle rules. This allows me to "Resume" (apply) later and pick up exactly where I left off without losing user data.

### 24. Explain the concept of "Namespace Isolation".
**Answer:**
It's a logical slicing of the cluster. Resources in the `dev` namespace cannot accidentally talk to `prod` (due to NetworkPolicies, if configured, or just DNS separation). It allows multiple teams or environments to share the same physical cluster (Control Plane and Worker Nodes), which maximizes resource utilization and minimizes the "control plane tax" (approx $70/month per cluster on AWS).

---

## 🚀 Section 4: CI/CD & DevOps

### 25. Walk me through your "Data-as-Code" pipeline.
**Answer:**
In `data-sync.yml`, I use the `on: push` trigger filtered to the `data/` directory.
1.  **Detect**: The workflow starts when `data/*.pdf` is pushed.
2.  **Upload**: It syncs the file to S3.
3.  **Process**: It triggers a script that calls the Embedding Service to index the new file.
This means the state of my Knowledge Base is version-controlled in Git. I can roll back a document change just by reverting the git commit.

### 26. How do you ensure code quality in CI?
**Answer:**
My `ci.yml` pipeline enforces strict quality gates:
1.  **Format**: `black` checks code style.
2.  **Lint**: `pylint` checks for code errors and smells.
3.  **Type Check**: `mypy` enforces static typing (critical for complex Python apps).
4.  **Test**: `pytest` runs unit tests.
5.  **Security**: `trivy` scans the Docker image for vulnerabilities.
The PR cannot be merged unless all these turn green.

### 27. What is your containerization strategy?
**Answer:**
I use a multi-stage Dockerfile.
- **Stage 1 (Builder)**: Installs compilers and builds heavy dependencies.
- **Stage 2 (Runtime)**: Copies only the necessary artifacts to a slim python image.
This keeps the image size small (~200MB vs ~1GB), which speeds up Kubernetes deployments and reduces the attack surface.

### 28. How does the CD pipeline work?
**Answer:**
It's an automated promotion strategy:
- **Dev**: Deploys automatically on every merge to `main`.
- **Staging**: Triggered manually via GitHub Actions workflow dispatch.
- **Prod**: Triggered manually but requires an **Approval** from the "Environment Protection" rules in GitHub. This segregates duties—a developer can't accidentally push to prod without a second pair of eyes.

### 29. How do you handle secrets?
**Answer:**
I **never** commit secrets to Git.
- **Local**: I use `.env` files (ignored by git).
- **CI/CD**: GitHub Secrets store AWS credentials.
- **Kubernetes**: I use the **External Secrets Operator** (or standard Kubernetes Secrets) to inject sensitive implementation details (like DB passwords) as environment variables into the pods at runtime.

### 30. What is "Drift Detection" in your MLOps pipeline?
**Answer:**
Data Drift happens when the user's questions change over time (e.g., users start asking about a new product you haven't documented). My `drift_detector.py` uses statistical tests (like Kolmogorov-Smirnov) to compare the distribution of recent queries against the historical baseline. If the "Query Conceptual Distance" shifts significantly, it alerts the team that we need to update our prompt or knowledge base.

---

## 📈 Section 5: MLOps & Observability

### 31. What metrics are you tracking in Prometheus?
**Answer:**
I track three "Golden Signals" of LLMOps:
1.  **RAG Latency**: How long the whole chain takes (P95 histogram).
2.  **Token Usage**: Input/Output token counts (Counter) to calculate exact costs.
3.  **Cost Estimates**: Real-time dollar spend accumulation based on model pricing.
Additionally, I track operational metrics like **Cache Hit Rate** (to prove ROI) and **Ingestion Success Rate**.

### 32. How do you test the quality of the RAG answers?
**Answer:**
I built an automated component `api/evaluation/quality_metrics.py`. It uses "LLM-as-a-Judge".
- We take a dataset of (Question, Context, Answer).
- We ask a stronger model (Nova 2 Pro) to score the answer on:
    - **Relevance**: Did it answer the user's specific question?
    - **Faithfulness**: Did it stick to the context provided?
This runs as part of the pipeline to regression-test changes to the prompt or retrieval logic.

### 33. Explain Prompt Versioning in your project.
**Answer:**
Prompts are code. I don't hardcode strings in the `rag_service.py`. Instead, `prompt_manager` loads prompts from versioned files/configurations. This allows me to A/B test "Prompt V1" (Creative) vs "Prompt V2" (Concise) and track which one performs better in MLflow, associating metrics like token usage and user feedback with specific prompt versions.

### 34. What is MLflow used for here?
**Answer:**
MLflow is my **Experiment Tracker**. When I'm tuning the system (e.g., changing the chunk size from 1000 to 500), I log the run to MLflow. It records the parameters (chunk_size=500) and the resulting metrics (retrieval_accuracy=0.85). This gives me a scientific record of what configuration works best, rather than guessing.

### 35. How do you monitor the "Drift" of the Vector DB?
**Answer:**
As documents are added/removed, the vector space changes. My Monitoring suite tracks the "Center of Mass" of the document clusters. If new documents are skewing significantly away from the existing clusters, it suggests we might need to re-index or adjust our retrieval parameters (like `alpha` in hybrid search) to accomodate the new domain.

---

## 🐍 Section 6: Python & Implementation Details

### 36. How does your `ingest_document` function handle concurrency?
**Answer:**
It is designed to be run as a **Background Task**. FastAPI accepts the upload and returns 202 using `BackgroundTasks`. The `ingest_document` function is asynchronous (`async def`). While it calls the Blocking I/O of S3 upload or Vector DB writing, it yields control, allowing the event loop to handle other incoming requests.

### 37. Implementation detail: How do you normalize text before embedding?
**Answer:**
In `api/data_pipeline/preprocess.py`, I implement specific cleaners:
- Removing excessive whitespace and newlines (which confuse embedding models).
- Standardizing bullet points.
- Removing generic headers/footers (page numbers) that would otherwise create "noise" chunks that match every query but contain no value.

### 38. How is the Redis connection managed?
**Answer:**
I use the **Singleton Pattern** in `api/services/cache_service.py`. The connection pool is initialized once on app startup (`@app.on_event("startup")`). This prevents the overhead of opening/closing a TCP connection to Redis for every single request, which is a common cause of high latency in rookie implementations.

### 39. Explain the Pydantic models in `query.py`.
**Answer:**
I define `QueryRequest(BaseModel)` to enforce the contract.
```python
class QueryRequest(BaseModel):
    question: str
    domain: str | None = None
```
If a user sends `{"q": "hello"}`, FastAPI automatically returns a 422 Error because `question` is missing. This prevents "NoneType" errors deep in the logic. It essentially provides strong typing for my JSON API.

### 40. Why do you use `pylint` AND `mypy`?
**Answer:**
They solve different problems.
- **Pylint** is a linter: It finds stylistic errors, unused variables, and potential bugs (dynamic analysis).
- **MyPy** is a static type checker: It ensures I'm not passing a `None` into a function that expects a `str`. In a complex RAG pipeline where data transforms through many stages, Type Safety is the best defense against runtime crashes.

---

## 🧭 Section 7: General & Behavioral (Project Context)

### 41. What was the hardest bug you faced in this project?
**Answer:**
*Contextual answer based on architecture*: "The hardest issue was handling the 'Cold Start' latency of the Vector DB connection in Kubernetes. Initially, the Readiness probe would fail because the app tried to connect before the DB sidecar was ready. I fixed this by implementing a retry-backoff mechanism in the `startup_event` and ensuring the Readiness probe correctly reflected the database connection status, not just the API process status."

### 42. If you had 2 more weeks, what would you add?
**Answer:**
I would implement **User Feedback Loops**. Adding a "Thumbs Up/Down" API endpoint that writes to a database. I would then use this data to fine-tune the routing logic (Reinforcement Learning from Human Feedback - RLHF), teaching the router which queries *actually* require the Pro model based on user satisfaction, rather than just heuristics.

### 43. How would you lower the latency of this system further?
**Answer:**
1.  **Streaming**: Switch the API to return `StreamingResponse`. This lowers the Time-To-First-Token (TTFT) from ~2s to ~200ms, making the app feel instant even if the full answer takes longer.
2.  **Optimized Embeddings**: Quantize the embeddings or use a smaller dimensionality (512 vs 1024) to speed up the vector dot products.

### 44. How does this project demonstrate "Senior" engineering traits?
**Answer:**
It moves beyond "Hello World" tutorials by addressing the unsexy constraints of reality: **Cost** and **Operations**.
- I didn't just build RAG; I built *Sustainable* RAG (Caching, Routing).
- I didn't just deploy; I built *Observable* deployments (Metrics, Logging).
- I didn't just code; I built *Lifecycle* (CI/CD, Tests).
It shows I care about the "Day 2" problems of running software, not just the "Day 1" fun of building it.

### 45. Explain "Recursion" in the context of your chunking strategy.
**Answer:**
I use a `RecursiveCharacterTextSplitter`. Instead of blindly chopping every 1000 chars, it recursively tries to split by the "most important" separators first: Paragraphs (`\n\n`), then Sentences (`.`), then Words (` `). This attempts to keep semantically related text together in one chunk, rather than cutting a sentence in half just to meet a character limit.

### 46. What security measures are in place?
**Answer:**
1.  **Network**: The database is not exposed to the public internet (ClusterIP only).
2.  **Application**: Bedrock Guardrails filters attacks.
3.  **Infrastructure**: IAM Roles (IRSA) enforce least privilege (Pod can only read its specific S3 bucket).
4.  **Content**: File uploads are validated for type and size to prevent DoS attacks.

### 47. Why Terraform Modules?
**Answer:**
DRY (Don't Repeat Yourself). I defined the standard configuration for "My Company's S3 Bucket" (Encrypted, Versioned, Tagged) once in a module. I then instantiate this module for `dev` and `prod`. If security requirements change (e.g., "Must use KMS"), I update the module file once, and all environments inherit the fix on the next apply.

### 48. How do you handle database migrations in this setup?
**Answer:**
For ChromaDB (which is file-based/embedded in this context), "migrations" usually mean re-indexing. My `data-sync` pipeline handles this. If I change the embedding model, I would trigger a "Re-ingest" job that clears the collection and re-processes the source documents from S3 to regenerate vectors with the new model.

### 49. How would you add a new domain (e.g., "Finance") to the system?
**Answer:**
1.  **Config**: Update `routing_service.py` with the new domain rules (defaults to Pro or Lite).
2.  **Infrastructure**: Create a new S3 folder `data/finance/`.
3.  **UI**: The `GET /domains` endpoint automatically picks up the configuration implies minimal code changes.
4.  **Ingestion**: Upload documents to the new folder; the pipeline handles the rest.

### 50. Final Question: Is this production ready?
**Answer:**
It is "Architecturally Ready" for production, but "Operationally Scoped" for a portfolio.
- **Ready**: The Architecture (Hub-Spoke), Security (IAM/Guardrails), and Observability (Prometheus) are production-grade.
- **Not Ready**: I am using a single instance of ChromaDB (Single Point of Failure) and Spot Instances (potential interruption). For true Enterprise Production, I would swap ChromaDB for a managed vector DB (like Pinecone or AWS OpenSearch Serverless) and use On-Demand nodes for the API.
