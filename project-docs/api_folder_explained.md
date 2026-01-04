# API Folder Structure and Functionality

## Overview

The `api/` folder contains the FastAPI application that serves as the backend for the RAG (Retrieval-Augmented Generation) system. It handles document uploads, query processing, and integrates with AWS Bedrock services.

---

## Folder Structure

```
api/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── Dockerfile                   # Container definition
├── requirements.txt             # Python dependencies
│
├── routers/                     # API route handlers
│   ├── documents.py             # Document upload/delete
│   ├── query.py                 # Q&A endpoints
│   └── health.py                # Health checks
│
├── services/                    # Business logic
│   ├── embedding_service.py     # Titan Embeddings V2
│   ├── llm_service.py           # Amazon Nova 2
│   ├── vector_store_service.py  # ChromaDB/Weaviate
│   ├── cache_service.py         # Redis semantic caching
│   └── guardrails_service.py    # Bedrock Guardrails
│
├── models/                      # Pydantic schemas
│   └── schemas.py
│
└── utils/                       # Helper functions
    ├── chunking.py              # Document chunking
    └── hybrid_search.py         # Vector + keyword search
```

---

## File Descriptions

### Root Level Files

#### `main.py` - Application Entry Point

**Purpose:** Initialize and configure the FastAPI application

**Responsibilities:**
- Create FastAPI app instance
- Configure CORS middleware
- Set up logging and error handlers
- Register all routers (documents, query, health)
- Initialize connections on startup:
  - Redis cache
  - Vector database (ChromaDB/Weaviate)
  - AWS Bedrock clients
- Clean up connections on shutdown

**Key Features:**
- Startup event handlers
- Shutdown event handlers
- Global exception handling
- Request/response logging
- Prometheus metrics endpoint

---

#### `config.py` - Configuration Management

**Purpose:** Centralized configuration using environment variables

**Configuration Categories:**

**AWS Settings:**
- AWS region
- AWS credentials (from environment)
- Bedrock model IDs (Nova 2 Lite, Nova 2 Pro)
- Titan Embeddings V2 model ID
- S3 bucket names (documents, embeddings)

**Vector Database:**
- Connection URL
- Collection name
- Persistence directory (for ChromaDB)

**Redis Cache:**
- Host and port
- Password
- TTL settings
- Similarity threshold for cache hits

**Application Settings:**
- Chunk size and overlap
- Retrieval-k (number of documents to retrieve)
- Domain configurations
- Logging level

**Security:**
- API keys
- CORS allowed origins
- Rate limiting settings

---

#### `Dockerfile` - Container Definition

**Purpose:** Build Docker image for deployment

**Stages:**
- Base image: Python 3.11-slim
- Install system dependencies
- Copy and install Python requirements
- Copy application code
- Expose port 8000
- Set up non-root user
- Run with uvicorn

**Design Rationale:**
- **Microservices Pattern:** The Dockerfile is placed inside the `api/` folder to keep the service self-contained. Each service in the project (api, frontend, etc.) manages its own build instructions.
- **Build Efficiency:** Keeping the Dockerfile close to the code allows for a cleaner separation of concerns.
- **Portability:** The `api/` folder can be moved or reused in other projects as a complete, buildable unit.

**Usage:**
To build the image correctly while allowing Python to see the package structure, run the build from the **project root**:
```bash
docker build -t llmops-api -f api/Dockerfile .
```
> [!NOTE]
> We use the `-f` flag to point to the Dockerfile inside the `api/` folder, but use the root directory (`.`) as the build context so that the `COPY` commands can access the `api/` directory structure correctly.

---

#### `requirements.txt` - Python Dependencies

**Key Packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `boto3` - AWS SDK
- `langchain` - RAG orchestration
- `langchain-aws` - Bedrock integration
- `chromadb` or `weaviate-client` - Vector database
- `redis` - Caching
- `pypdf` - PDF processing
- `python-docx` - DOCX processing
- `pydantic` - Data validation
- `prometheus-client` - Metrics

---

## Routers (API Endpoints)

### `routers/documents.py` - Document Management

**Endpoints:**

**POST /documents/upload**
- Upload document via web UI
- Accepts: PDF, TXT, DOCX
- Parameters:
  - `file`: UploadFile
  - `domain`: str (Legal, HR, Marketing, etc.)
  - `tags`: List[str] (optional)
- Process:
  1. Validate file type and size
  2. Extract metadata
  3. Upload to S3
  4. Trigger embedding generation
  5. Store in vector database
- Returns: Document ID and metadata

**DELETE /documents/{doc_id}**
- Delete document from system
- Removes from S3 and vector database
- Returns: Success confirmation

**GET /documents/**
- List all documents
- Optional filters: domain, tags, date range
- Returns: List of document metadata

**GET /documents/{doc_id}**
- Get specific document metadata
- Returns: Full metadata including domain, tags, upload date

---

### `routers/query.py` - Q&A Endpoints

**Endpoints:**

**POST /query**
- Ask a question
- Parameters:
  - `question`: str
  - `domain`: str (optional filter)
  - `top_k`: int (default: 5)
- Process:
  1. Check semantic cache
  2. If cache miss:
     - Generate query embedding
     - Perform hybrid search (vector + keyword)
     - Apply domain filter
     - Retrieve top-k documents
     - Select LLM model (intelligent routing)
     - Generate response with domain-specific prompt
     - Apply guardrails
     - Cache response
  3. Track metrics (latency, cost, quality)
- Returns:
  - Answer
  - Source documents with citations
  - Confidence score
  - Cost breakdown

**POST /query/batch**
- Process multiple queries
- Useful for evaluation
- Returns: Array of responses

**GET /query/history**
- Get query history
- Optional filters: domain, date range
- Returns: List of past queries and responses

---

### `routers/health.py` - Health Checks

**Endpoints:**

**GET /health**
- Basic health check
- Returns: `{"status": "healthy"}`

**GET /health/ready**
- Readiness probe for Kubernetes
- Checks:
  - Vector database connection
  - Redis connection
  - AWS Bedrock access
- Returns: Ready status or error details

**GET /health/live**
- Liveness probe for Kubernetes
- Checks if application is running
- Returns: Live status

---

## Services (Business Logic)

### `services/embedding_service.py` - Embeddings

**Purpose:** Generate embeddings using AWS Bedrock Titan Embeddings V2

**Functions:**

**`generate_embedding(text: str) -> List[float]`**
- Generate embedding for single text
- Calls Titan Embeddings V2 API
- Returns: 1024-dimensional vector

**`generate_batch_embeddings(texts: List[str]) -> List[List[float]]`**
- Batch processing for efficiency
- Handles rate limiting
- Returns: List of embeddings

**`calculate_similarity(emb1: List[float], emb2: List[float]) -> float`**
- Calculate cosine similarity
- Used for semantic caching
- Returns: Similarity score (0-1)

**Features:**
- Error handling and retries
- Rate limiting
- Cost tracking
- Prometheus metrics

---

### `services/llm_service.py` - LLM Integration

**Purpose:** Call Amazon Nova 2 for text generation

**Functions:**

**`generate_response(prompt: str, model: str = "lite") -> str`**
- Generate answer using Nova 2
- Supports both Lite and Pro models
- Handles token limits
- Returns: Generated text

**`select_model(query_complexity: str, domain: str) -> str`**
- Intelligent routing logic
- Simple + HR → Nova 2 Lite
- Complex + Legal → Nova 2 Pro
- Returns: Model ID

**`apply_domain_prompt(domain: str, context: str, question: str) -> str`**
- Domain-specific prompt templates
- Legal: Citation-based, formal
- HR: Friendly, policy-based
- Marketing: Creative, brand-aware
- Engineering: Technical, precise
- Returns: Formatted prompt

**`analyze_query_complexity(query: str) -> str`**
- Determine if query is simple or complex
- Based on: length, keywords, question type
- Returns: "simple" or "complex"

**Features:**
- Token usage tracking
- Cost calculation
- Model selection optimization
- Prometheus metrics

---

### `services/vector_store_service.py` - Vector Database

**Purpose:** Manage vector database operations (ChromaDB or Weaviate)

**Functions:**

**`add_documents(docs: List[str], embeddings: List[List[float]], metadata: List[dict])`**
- Store document chunks with embeddings
- Metadata includes: domain, tags, doc_id, chunk_id
- Handles batch inserts

**`search(query_embedding: List[float], filters: dict, top_k: int) -> List[dict]`**
- Vector similarity search
- Apply metadata filters (domain, tags)
- Returns: Top-k most similar documents

**`hybrid_search(query: str, domain_filter: str, top_k: int) -> List[dict]`**
- Combine vector and keyword search
- Vector search for semantic similarity
- BM25 for keyword matching
- Merge and rerank results
- Returns: Top-k documents

**`delete_document(doc_id: str)`**
- Remove all chunks for a document
- Clean up from vector database

**Features:**
- Connection pooling
- Error handling
- Performance monitoring

---

### `services/cache_service.py` - Semantic Caching

**Purpose:** Redis-based semantic caching for LLM responses

**Functions:**

**`get_cached_response(query_embedding: List[float]) -> Optional[str]`**
- Check if similar query exists in cache
- Calculate similarity with cached queries
- If similarity > threshold (0.95), return cached response
- Returns: Cached response or None

**`cache_response(query_embedding: List[float], response: str, ttl: int = 3600)`**
- Store response in Redis
- Key: embedding hash
- Value: response + metadata
- Set TTL (default 1 hour)

**`calculate_cache_similarity(emb1: List[float], emb2: List[float]) -> float`**
- Cosine similarity calculation
- Returns: Similarity score

**`get_cache_stats() -> dict`**
- Cache hit rate
- Cost savings
- Total queries cached
- Returns: Statistics dictionary

**Features:**
- Configurable similarity threshold
- TTL-based expiration
- Cost savings tracking
- Prometheus metrics

---

### `services/guardrails_service.py` - Safety

**Purpose:** AWS Bedrock Guardrails integration for safety and compliance

**Functions:**

**`apply_guardrails(text: str) -> dict`**
- Apply all guardrails to text
- PII masking (SSN, email, phone)
- Content filtering (hate speech, violence)
- Topic boundaries
- Returns: Filtered text + violations

**`validate_query(query: str) -> bool`**
- Check query before processing
- Block inappropriate queries
- Returns: True if valid

**`validate_response(response: str) -> bool`**
- Check response before returning
- Ensure no PII leakage
- Ensure appropriate content
- Returns: True if valid

**`log_violations(violation_type: str, content: str)`**
- Audit logging for compliance
- Track all violations
- Store in CloudWatch

**Features:**
- Configurable guardrail policies
- Audit logging
- Compliance reporting

---

## Models (Data Validation)

### `models/schemas.py` - Pydantic Schemas

**Purpose:** Request/response validation and serialization

**Models:**

**`DocumentUploadRequest`**
```python
- file: UploadFile
- domain: str
- tags: Optional[List[str]]
```

**`QueryRequest`**
```python
- question: str
- domain: Optional[str]
- top_k: int = 5
```

**`QueryResponse`**
```python
- answer: str
- sources: List[dict]
- confidence: float
- cost: float
- cached: bool
```

**`DocumentMetadata`**
```python
- doc_id: str
- filename: str
- domain: str
- tags: List[str]
- upload_date: datetime
- size: int
```

**`HealthResponse`**
```python
- status: str
- checks: dict
- timestamp: datetime
```

---

## Utils (Helper Functions)

### `utils/chunking.py` - Document Chunking

**Purpose:** Split documents into optimal chunks for embedding

**Functions:**

**`chunk_document(text: str, strategy: str = "recursive") -> List[str]`**
- Recursive character splitting (default)
- Preserves sentence boundaries
- Configurable chunk size and overlap
- Returns: List of text chunks

**`calculate_optimal_chunk_size(doc_type: str) -> int`**
- Adaptive chunk sizing
- PDF: 1000 chars
- TXT: 800 chars
- DOCX: 1200 chars
- Returns: Optimal chunk size

**`preserve_context(chunks: List[str], overlap: int = 200) -> List[str]`**
- Add overlap between chunks
- Maintains context across boundaries
- Returns: Chunks with overlap

**Features:**
- Multiple chunking strategies
- Configurable parameters
- Context preservation

---

### `utils/hybrid_search.py` - Search Logic

**Purpose:** Combine vector and keyword search results

**Functions:**

**`hybrid_search(query: str, vector_results: List[dict], keyword_results: List[dict]) -> List[dict]`**
- Merge vector and keyword search results
- Weighted scoring (70% vector, 30% keyword)
- Deduplicate results
- Returns: Merged and ranked results

**`rerank_results(results: List[dict], query: str) -> List[dict]`**
- Rerank based on relevance
- Consider: similarity score, domain match, recency
- Returns: Reranked results

**`apply_domain_filter(results: List[dict], domain: str) -> List[dict]`**
- Filter results by domain
- Returns: Filtered results

**Features:**
- Configurable weights
- Multiple ranking strategies
- Domain-aware filtering

---

## Request Flow Example

### User Asks a Question

```
1. User → POST /query {"question": "What's our remote work policy?", "domain": "HR"}
   ↓
2. routers/query.py receives request
   ↓
3. services/cache_service.py checks Redis cache
   ↓ (cache miss)
4. services/embedding_service.py generates query embedding
   ↓
5. services/vector_store_service.py performs hybrid search with HR filter
   ↓
6. services/llm_service.py:
   - Analyzes complexity → "simple"
   - Selects model → Nova 2 Lite
   - Applies HR-specific prompt
   - Generates response
   ↓
7. services/guardrails_service.py validates response
   ↓
8. services/cache_service.py caches response
   ↓
9. routers/query.py returns response with sources and cost
```

---

## Design Principles

### Separation of Concerns
- **Routers:** HTTP layer only
- **Services:** Business logic
- **Models:** Data validation
- **Utils:** Reusable helpers

### Domain-Driven Design
- Domain-specific prompts
- Domain filtering
- Domain-aware routing

### Cost Optimization
- Semantic caching (70% reduction)
- Intelligent routing (60% reduction)
- Token optimization

### Observability
- Prometheus metrics in every service
- Cost tracking per query
- Performance monitoring
- Error tracking

### Scalability
- Stateless design
- Connection pooling
- Async operations
- Horizontal scaling ready

---

## Implementation Phases

**Phase 1: Foundation**
- `main.py`, `config.py`, `requirements.txt`
- Basic structure

**Phase 3: Core Features**
- All routers
- All services
- All models
- All utils

**Phase 5: Monitoring**
- Add Prometheus metrics
- Performance tracking

**Phase 6: MLOps**
- Enhance caching
- Intelligent routing
- Cost optimization

---

This API structure ensures the application is **modular, testable, maintainable, and production-ready**.
