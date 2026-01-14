# 🎯 LLMOps RAG Pipeline: Advanced Technical Interview Guide (Part 2)

**Project**: `llmops-rag-pipeline`
**Purpose**: This guide covers deeper technical scenarios, edge cases, and implementation specifics not addressed in Part 1.

---

## 🔬 Section 1: Deep Dive - Implementation Details

### 1. Walk through the exact sequence of function calls when a user submits a query.
**Answer:**
1.  `query.py::query_rag()` receives the POST request.
2.  `drift_detector.record_query()` logs the query for drift analysis.
3.  `embedding_service.generate_embedding()` converts the question to a vector.
4.  `cache_service.find_similar_response()` checks Redis for a semantic cache hit.
5.  If miss: `routing_service.analyze_complexity()` determines the model tier (Lite/Pro).
6.  `vector_store.hybrid_search()` retrieves Top-K context chunks.
7.  `prompt_manager.get_prompt()` assembles the final system/user prompts.
8.  `llm_service.generate_response()` calls AWS Bedrock.
9.  `cache_service.set_response()` stores the new result in Redis.
10. Prometheus metrics are updated via `_track_metrics()`.

### 2. How does the `find_similar_response` function in `cache_service.py` work internally?
**Answer:**
It iterates through cached responses in Redis (up to 100 keys for performance). For each cached entry, it retrieves the stored `query_embedding` and computes the **cosine similarity** against the current query's embedding. If the similarity exceeds the threshold (0.95), it returns the cached response and the similarity score. This allows semantically equivalent but lexically different questions to hit the cache.

### 3. Why is there a limit of 100 keys in the cache similarity search?
**Answer:**
This is a performance trade-off. Iterating through every key in Redis is O(N) complexity. As the cache grows, this scan could add hundreds of milliseconds of latency. Limiting to 100 most recent keys (LRU) ensures the cache lookup remains sub-10ms, which is critical for the user experience. A more scalable solution would use a dedicated vector search index (like Redis Vector Similarity Search or Pinecone).

### 4. What is the difference between `embedding_ttl` (24 hours) and `response_ttl` (1 hour) in the cache?
**Answer:**
Embeddings are deterministic: the same text will always produce the same vector from Titan V2. So they can be cached for longer without risk of staleness. Responses, however, depend on the *context retrieved from the Vector DB*. If new documents are added, an old cached response might be outdated or incomplete. The shorter TTL ensures users get answers reflecting the latest knowledge base state.

### 5. How do you invalidate the cache when new documents are added?
**Answer:**
The `cache_service.invalidate_domain(domain)` function is designed for this. It uses a `KEYS` command with a wildcard pattern (`response:{domain}:*`) and deletes all matching keys. This should be called at the end of the `ingest_document` pipeline to ensure stale cached answers for that domain are cleared.

### 6. In `routing_service.py`, how is the complexity score calculated?
**Answer:**
It's a weighted sum of heuristics:
- `(word_count > threshold) * 2` – Long queries get 2 points.
- `(sentence_count > threshold) * 1` – Multi-sentence queries get 1 point.
- `has_technical_terms * 1` – Presence of domain jargon.
- `has_multiple_questions * 1` – More than one `?` mark.
- `has_conditional * 1` – Keywords like "if", "when", "unless".
If the score is >= 3, the query is routed to the **Pro** model.

### 7. What happens if the Vector DB returns zero results?
**Answer:**
The `context_text` variable becomes an empty string. The prompt is still constructed and sent to the LLM, but the system prompt instructs Nova 2: "If there is no relevant information in the context, say you don't know." This fallback prevents the model from hallucinating an answer and maintains user trust.

### 8. How do you prevent a user from uploading a 1GB file and crashing the pod?
**Answer:**
File validation happens in `documents.py::validate_file()`:
- `MAX_FILE_SIZE = 10 * 1024 * 1024` (10MB limit).
- We check the size by seeking to the end of the file object (`file.file.seek(0, 2)`).
- If exceeded, we raise an `HTTPException` with status 400 before any processing begins. This is a "fail-fast" pattern.

---

## 🧩 Section 2: LangChain & Prompting

### 9. Where is LangChain used in this project, and what components do you use?
**Answer:**
LangChain is used implicitly through patterns rather than direct library imports in the main RAG service. The pipeline follows the LangChain conceptual model: **Retriever -> Prompt Template -> LLM -> Output Parser**. Specifically, `vector_store.py` acts as the Retriever, `prompt_manager.py` handles templates, and `llm_service.py` wraps the LLM. This custom implementation gives finer control than using LangChain's high-level chains.

### 10. How are prompts versioned and managed?
**Answer:**
The `api/prompts/versions.py` file contains a `PromptManager` class. It stores multiple versions of prompts (e.g., "v1_concise", "v2_detailed") and can select which one to use based on configuration or A/B test assignment. The version ID is logged with every query to MLflow, allowing us to correlate answer quality metrics with specific prompt versions.

### 11. What is the structure of a system prompt in this project?
**Answer:**
A typical system prompt includes:
1.  **Role Definition**: "You are a helpful assistant specializing in {domain}."
2.  **Instructions**: "Answer using ONLY the provided context. If the answer is not in the context, say 'I don't have information on that.'"
3.  **Constraints**: "Be concise. Cite your sources."
This structure grounds the model and reduces hallucinations.

### 12. How would you implement "Chain of Thought" prompting in this system?
**Answer:**
I would modify the `prompt_manager` to add an intermediate reasoning step. Before asking for the final answer, the prompt would include: "First, list the relevant facts from the context. Then, explain your reasoning step by step. Finally, provide your answer." This encourages the model to "show its work," improving accuracy on complex, multi-hop questions.

### 13. What is the "Context Window" and why is it a constraint?
**Answer:**
The Context Window is the maximum number of tokens (text units) the LLM can process in a single request (input + output). For Nova 2 Lite, this might be 32k tokens. If my retrieved context + prompt + expected answer exceeds this, the request will fail or be truncated. This is why chunking strategy is critical: we must retrieve enough context to answer without exceeding the window.

---

## 🐳 Section 3: Docker & Containerization

### 14. Explain the contents of your `Dockerfile` for the API.
**Answer:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api/ ./api/
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
This is a simple single-stage build. It uses a slim base image for size, copies dependencies first (for layer caching), then copies the application code.

### 15. How does `.dockerignore` improve your build process?
**Answer:**
The `.dockerignore` file excludes unnecessary files from the Docker build context (e.g., `.git/`, `__pycache__/`, `.venv/`, `*.md`). This speeds up the `COPY` command because Docker doesn't transfer gigabytes of unneeded data. It also reduces the final image size and prevents accidentally including secrets from `.env` files.

### 16. What is the difference between `COPY` and `ADD` in a Dockerfile?
**Answer:**
`COPY` simply copies files from the host to the image. `ADD` has additional features: it can fetch files from a URL and automatically unpack tar archives. Best practice is to use `COPY` unless you specifically need `ADD`'s features, as `COPY` is more predictable and explicit.

### 17. Why use `--no-cache-dir` with `pip install`?
**Answer:**
This flag tells pip not to save downloaded packages in a local cache. Since we're building a container image (which is itself a form of cache), keeping pip's internal cache is redundant and wastes disk space. It can reduce the final image size by 50-100MB.

### 18. How would you implement a multi-stage build for this project?
**Answer:**
```dockerfile
# Stage 1: Builder
FROM python:3.12 AS builder
WORKDIR /app
COPY api/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY api/ ./api/
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
The builder stage compiles dependencies (some may require compilers). The runtime stage only copies the pre-built wheels, keeping the final image lean.

---

## ☁️ Section 4: AWS Services Deep Dive

### 19. Explain the role of the S3 bucket in this architecture.
**Answer:**
S3 serves as the **durable source of truth** for documents. When a user uploads a file, it's first stored in S3 (`s3_service.upload_file()`). This ensures that even if the Vector DB is re-indexed or wiped, the original documents are preserved. The `data-sync` pipeline also reads from S3, making it the single point of integration for both ingestion paths.

### 20. What is a "Global Inference Profile" in AWS Bedrock?
**Answer:**
A Global Inference Profile (e.g., `global.amazon.nova-2-lite-v1:0`) allows Bedrock to automatically route LLM inference requests to the optimal AWS region based on availability and latency. This provides built-in resilience: if one region is overloaded or down, your requests are served from another without any code changes.

### 21. How does IRSA (IAM Roles for Service Accounts) work at a technical level?
**Answer:**
1.  When the EKS cluster is created, an **OIDC Provider** is registered with AWS IAM.
2.  An IAM Role is created with a trust policy that allows the OIDC provider to assume it.
3.  A Kubernetes ServiceAccount is annotated with `eks.amazonaws.com/role-arn: <IAM_ROLE_ARN>`.
4.  When a pod uses this ServiceAccount, the AWS SDK in the pod automatically retrieves temporary credentials from the OIDC provider via a projected token volume.
This eliminates the need to store long-lived AWS keys in the cluster.

### 22. What is the EBS CSI Driver and why is it needed for ChromaDB?
**Answer:**
The **EBS Container Storage Interface (CSI) Driver** is an add-on for EKS that allows Kubernetes to dynamically provision and mount AWS EBS volumes as PersistentVolumes. ChromaDB stores its vector index on disk; without persistent storage, the index would be lost on pod restart. The CSI driver bridges the gap between Kubernetes' abstract storage model and AWS's block storage.

### 23. How do you configure Bedrock Guardrails?
**Answer:**
Guardrails are configured in the AWS Console (or via Terraform/CDK):
1.  **Create a Guardrail**: Define a name and description.
2.  **Add Content Filters**: Set strictness for topics like violence, hate speech.
3.  **Add Denied Topics**: Create custom topic definitions (e.g., "competitor products").
4.  **Add PII Filters**: Select data types to mask (SSN, email, phone).
5.  **Associate with Model**: Apply the Guardrail ID when calling Bedrock's `invoke_model` API.

### 24. What AWS service would you use to implement streaming responses?
**Answer:**
AWS Bedrock supports streaming via `invoke_model_with_response_stream`. The API returns an event stream, and you can yield chunks to the client as they arrive. In FastAPI, this is implemented using `StreamingResponse`. This drastically reduces perceived latency (Time-To-First-Token).

---

## ⚙️ Section 5: Debugging & Scenario-Based Questions

### 25. The API is returning 503 errors. How do you debug this?
**Answer:**
1.  **Check Pod Status**: `kubectl get pods -n dev` – Is the pod running? Restarting?
2.  **Check Logs**: `kubectl logs <pod-name> -n dev` – Look for Python exceptions.
3.  **Check Readiness Probe**: If failing, the Service won't route traffic. `kubectl describe pod <pod-name>` shows probe status.
4.  **Check Dependencies**: Can the pod reach Redis, ChromaDB, Bedrock? Network issues cause timeouts.

### 26. ChromaDB is slow. What are your optimization vectors?
**Answer:**
1.  **Increase Resources**: ChromaDB is CPU/RAM intensive. Check if the pod is being throttled (`kubectl top pod`).
2.  **Reduce Top-K**: Retrieving 10 documents is faster than 50.
3.  **Use HNSW Index**: Ensure ChromaDB is configured with an optimized index (HNSW is default).
4.  **Warm Up**: The first query after a restart is slow due to index loading. Implement a startup probe to pre-warm.

### 27. A user reports that the LLM gave an answer that contradicts the source document. What do you check?
**Answer:**
1.  **Retrieval Quality**: Query the Vector DB manually with the user's question. Are the correct chunks being retrieved? If not, it's a retrieval/chunking problem.
2.  **Context Injection**: Log the exact prompt sent to the LLM. Is the relevant context actually included?
3.  **Prompt Clarity**: Is the system prompt clear enough? Add stricter grounding instructions.
4.  **Guardrails**: Did the Guardrail modify the response?

### 28. How would you test the system's behavior under high load?
**Answer:**
I would use a load testing tool like **Locust** or **k6**:
1.  Define a scenario that simulates realistic query patterns.
2.  Ramp up concurrent users (e.g., 10 -> 100 -> 500).
3.  Monitor Grafana dashboards for latency percentiles (P50, P95, P99).
4.  Monitor `kubectl top pods` for resource saturation.
5.  Identify the "breaking point" where latency degrades or errors spike.

### 29. The `data-sync` workflow failed. How do you investigate?
**Answer:**
1.  Check GitHub Actions logs: Navigate to the workflow run in the "Actions" tab.
2.  Identify the failing step: Was it S3 upload? Embedding generation?
3.  Check secrets: Are `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` correctly configured in GitHub Secrets?
4.  Re-run manually: Trigger the workflow again with "Re-run all jobs."

### 30. Prometheus shows zero metrics for `rag_cost_dollars_total`. Why?
**Answer:**
1.  **Endpoint Check**: `curl http://<pod-ip>:8000/metrics` – Is the metric exposed?
2.  **Counter Initialization**: Prometheus Counters start at 0. If no queries have been made, the metric won't appear until `.inc()` is called at least once.
3.  **ServiceMonitor**: Is the `ServiceMonitor` correctly targeting the pod's label (`app: rag-api`)? Check with `kubectl get servicemonitor -n monitoring -o yaml`.
4.  **Scrape Config**: In Prometheus UI, go to "Targets". Is your target listed and healthy?

---

## 🏛️ Section 6: System Design Trade-offs

### 31. Why ChromaDB instead of Pinecone or Weaviate?
**Answer:**
**ChromaDB** is chosen for its simplicity and self-hosted nature. For a portfolio project, running a managed service like Pinecone adds cost, while ChromaDB runs for "free" on my existing K8s nodes. It also gives me full operational experience (backups, scaling), which is the point of this project. For production at scale, I would consider **Pinecone** for its serverless model and automatic scaling.

### 32. What are the trade-offs of using a single EKS cluster for all environments?
**Answer:**
**Pros**: Lower cost (shared control plane), simpler management.
**Cons**: "Noisy neighbor" risk (a runaway dev pod could consume resources meant for prod), blast radius (a misconfiguration affects all environments). Mitigations include ResourceQuotas per namespace and strong RBAC policies.

### 33. Why use Redis for semantic caching instead of an in-memory Python dict?
**Answer:**
1.  **Persistence**: Redis data survives pod restarts.
2.  **Scalability**: If I scale the API to multiple replicas, an in-memory dict is local to each pod. Redis provides a shared cache accessible by all replicas.
3.  **Eviction Policies**: Redis has built-in LRU (Least Recently Used) eviction, preventing unbounded memory growth.

### 34. What is the "Re-Ranking" problem and how would you address it?
**Answer:**
Hybrid search returns a combined score, but the top results might not always be the most relevant for the specific question. **Re-ranking** is a second-pass step using a more sophisticated model (e.g., a cross-encoder like `sentence-transformers/ms-marco-MiniLM-L-6-v2`) to re-evaluate the top 20 results and pick the best 3. This adds latency but significantly improves precision.

### 35. How would you handle multi-lingual documents?
**Answer:**
1.  **Multi-lingual Embeddings**: Use an embedding model that supports multiple languages (e.g., `multilingual-e5-large`).
2.  **Language Detection**: Detect the query's language and add a metadata filter to prefer documents in the same language.
3.  **Translation Layer**: If needed, translate the query to English before embedding (if the knowledge base is English-only).

---

## 📊 Section 7: Observability & Governance

### 36. How do you differentiate between a "slow LLM" and a "slow Vector DB" in your metrics?
**Answer:**
I use the `RAG_REQUEST_LATENCY` histogram with a `stage` label:
- `stage="retrieval"`: Time spent in `vector_store.hybrid_search()`.
- `stage="generation"`: Time spent in `llm_service.generate_response()`.
- `stage="total"`: End-to-end time.
In Grafana, I can create separate panels for each stage to pinpoint bottlenecks.

### 37. How do you calculate the exact dollar cost of each query?
**Answer:**
In `_track_metrics()`, I estimate token counts:
```python
input_tokens = len(prompt_text) / 4  # Rough estimate: 4 chars per token
output_tokens = len(response_text) / 4
cost = (input_tokens / 1000 * 0.00006) + (output_tokens / 1000 * 0.00024)
```
These are Bedrock's published prices for Nova 2 Lite. For Pro, the multipliers would be higher. This cost is then recorded in the `rag_cost_dollars_total` counter.

### 38. What is the Kolmogorov-Smirnov (K-S) test and why is it used for drift detection?
**Answer:**
The K-S test is a statistical test that compares the distributions of two datasets. In `drift_detector.py`, we compare the distribution of query embeddings from the past week against the overall historical distribution. If the K-S statistic is large (distributions are different), it indicates "drift"—users are asking about topics that weren't represented in training data or old queries.

### 39. How would you set up an alert for "Cost Anomaly"?
**Answer:**
In my `values.yaml` for the Prometheus stack, I define an alerting rule:
```yaml
- alert: HighCostSpike
  expr: rate(rag_cost_dollars_total[10m]) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "RAG API spending > $1/min detected"
```
This fires an alert if the cost rate exceeds a threshold for 5 consecutive minutes, indicating a potential runaway process or abuse.

### 40. What is the purpose of recording the `prompt_version` in MLflow?
**Answer:**
It enables **data-driven iteration**. If I A/B tested "Prompt V1" vs "Prompt V2" and tracked quality scores (from the evaluation pipeline) and user satisfaction (future thumbs up/down), I can run an MLflow query to see which version performed better. It moves prompt engineering from guesswork to science.

---

## 🔒 Section 8: Security & Compliance

### 41. How do you ensure PII is not stored in the Vector DB?
**Answer:**
1.  **Pre-processing**: A cleaning step in the ingestion pipeline can use regex or a library like `Presidio` to detect and redact PII (SSNs, emails) before embedding.
2.  **Bedrock Guardrails**: The guardrail can mask PII in the LLM's *output*, but not the input data itself. Input masking is our responsibility.

### 42. What is the principle of "Least Privilege" and where is it applied?
**Answer:**
It means granting only the minimum permissions necessary. In this project:
- The `rag-api` ServiceAccount can only `s3:GetObject` on its specific bucket, not all S3.
- The Terraform IAM user can only manage resources tagged with this project.
- The CI/CD GitHub Actions use scoped secrets, not root credentials.

### 43. How would you implement audit logging for sensitive queries?
**Answer:**
I would add a dedicated logging step in `query_rag()` that writes to a secure, tamper-evident store (e.g., AWS CloudWatch Logs with a retention policy, or a SIEM). The log would include: timestamp, user identifier (if auth is implemented), query text (hashed or redacted if sensitive), domain, and model used. This provides a forensic trail.

### 44. What security risk does the `allow_origins=["*"]` CORS setting introduce?
**Answer:**
This setting allows any website to make requests to my API using a user's browser session. If authentication is added later, a malicious website could trick a logged-in user into making unintended API calls. For production, I should restrict this to the specific frontend domain(s) (e.g., `allow_origins=["https://my-app.com"]`).

---

## 🛣️ Section 9: Future Roadmap & Growth

### 45. How would you add authentication to this API?
**Answer:**
I would integrate with **AWS Cognito** or a third-party provider like **Auth0**:
1.  Protect endpoints with a `Depends(oauth2_scheme)` in FastAPI.
2.  Validate JWT tokens on every request.
3.  Store user IDs in query logs for personalization and auditing.
This is listed as a "Future Enhancement" in the project tasks.

### 46. How would you implement a "Feedback Loop" for model improvement?
**Answer:**
1.  Add a `POST /feedback` endpoint accepting `{query_id, rating: "up"|"down"}`.
2.  Store feedback in a database tied to the query ID.
3.  Analyze: Which queries get low ratings? Correlate with domain, prompt version, model tier.
4.  Use this data to refine the routing logic (e.g., if "HR" queries with "Pro" model get more thumbs-up, adjust routing).

### 47. What is "Agentic RAG" and how would you evolve this project towards it?
**Answer:**
Agentic RAG allows the LLM to decide *which tools to use* to answer a question. Instead of a fixed pipeline (Retrieve -> Generate), the agent could:
- Decide to query the Vector DB *multiple times* with refined queries.
- Choose to call an external API (e.g., a calculator, a current weather service).
I would use a framework like **LangGraph** to implement this, defining a state machine where the LLM controls the transitions.

### 48. How would you support real-time document updates (e.g., a wiki that changes hourly)?
**Answer:**
1.  **Change Data Capture (CDC)**: Set up a trigger (e.g., S3 Event Notification, webhook from the wiki) that fires on document change.
2.  **Upsert Logic**: The ingestion service would receive the updated document, re-chunk, re-embed, and *replace* the old vectors in ChromaDB (using the document ID as the key).
3.  **Cache Invalidation**: Call `cache_service.invalidate_domain()` to prevent serving stale answers.

### 49. If you could start over, what would you do differently?
**Answer:**
I would adopt **OpenTelemetry** from day one for distributed tracing. While Prometheus metrics are great for aggregates, tracing allows me to follow a *single request* through every service hop. This is invaluable for debugging complex issues in a microservices architecture. I would also set up **structured JSON logging** instead of plain text for easier querying in CloudWatch Logs Insights.

### 50. What makes this project stand out compared to generic RAG tutorials?
**Answer:**
1.  **Operationalization**: It's not just about "getting an answer." It includes cost tracking, caching, routing, and observability—the "Day 2" concerns.
2.  **Infrastructure-as-Code**: Everything from the VPC to the Grafana dashboards is defined in Terraform and Helm, not hand-configured.
3.  **MLOps/LLMOps Practices**: Prompt versioning, experiment tracking (MLflow), drift detection, and automated evaluation pipelines.
4.  **Cost Governance**: A core design pillar, not an afterthought. The "Pause/Resume" strategy is a practical innovation for portfolio projects.

---

*Good luck with your interviews! Remember, the goal is to demonstrate not just that you *built* something, but that you *understand why* every component exists and how they interconnect.*
