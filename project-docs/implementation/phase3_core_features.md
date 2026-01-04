# Phase 3: Core Application Features - Implementation Plan

**Goal:** Transform the base API into a full-featured RAG platform. We will integrate the "brains" (AWS Bedrock) with the "memory" (Vector DB) and "logic" (LangChain), implementing the core value propositions of the project.

---

## 🏗️ Architectural Context

Phase 3 is the **System Integration** phase where independent components come together:
1.  **Computation**: FastAPI orchestrating the workflow.
2.  **Intelligence**: AWS Bedrock providing Nova 2 (LLM) and Titan V2 (Embeddings).
3.  **Memory**: ChromaDB/Weaviate providing vector search.
4.  **Security**: Bedrock Guardrails ensuring safety.

**Engineering Outcomes:**
- Production-grade RAG pipeline with Hybrid Search.
- Dual-path document ingestion (Real-time & Batch).
- Engineering domain-specific features (Metadata, Filtering).

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: AWS Bedrock Integration](#part-1-aws-bedrock-integration)**
- [1.1 Bedrock Client Service](#11-bedrock-client-service)
- [1.2 LLM Service (Nova 2)](#12-llm-service-nova-2)
- [1.3 Embedding Service (Titan V2)](#13-embedding-service-titan-v2)

**[Part 2: Vector Database & Storage](#part-2-vector-database--storage)**
- [2.1 Deploy ChromaDB (K8s)](#21-deploy-chromadb-k8s)
- [2.2 Vector Store Service](#22-vector-store-service)

**[Part 3: Document Processing](#part-3-document-processing)**
- [3.1 Chunking Utility](#31-chunking-utility)
- [3.2 Ingestion Service](#32-ingestion-service)
- [3.3 Document Upload Endpoint](#33-document-upload-endpoint)
- [3.4 GitHub Actions Data Sync](#34-github-actions-data-sync)

**[Part 4: The RAG Pipeline](#part-4-the-rag-pipeline)**
- [4.1 Retrieval & Generation Service](#41-retrieval--generation-service)
- [4.2 Query Endpoint](#42-query-endpoint)

**[Part 5: Domain Features & Frontend](#part-5-domain-features--frontend)**
- [5.1 Access Control Middleware](#51-access-control-middleware)
- [5.2 Analytics Service](#52-analytics-service)
- [5.3 Frontend UI Deployment](#53-frontend-ui-deployment)

**[Part 6: Verification Checklist](#part-6-verification-checklist)**

---

## Prerequisites

- **Phase 2 Complete**: API running on local Minikube.
- **AWS Access**: `llmops-admin` user with Bedrock access (`bedrock:InvokeModel`).
- **Python Deps**: `boto3`, `langchain`, `fastapi`, `chromadb`, `pypdf`, `tiktoken`.

---

## Part 1: AWS Bedrock Integration

### 1.1 Bedrock Client Service
**File:** `api/services/bedrock_service.py`

This service handles the raw connection to AWS.

```python
import boto3
import json
from api.config import settings

class BedrockClient:
    def __init__(self):
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.aws_region
        )

    def invoke(self, model_id: str, body: dict) -> dict:
        response = self.client.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        return json.loads(response['body'].read())

# Singleton instance
bedrock_client = BedrockClient()
```

### 1.2 LLM Service (Nova 2)
**File:** `api/services/llm_service.py`

Handles text generation with Amazon Nova 2.

```python
from api.services.bedrock_service import bedrock_client

class LLMService:
    def __init__(self, model_id="amazon.nova-2-lite-v1:0"):
        self.model_id = model_id

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        body = {
            "inferenceConfig": {"max_new_tokens": 1000},
            "messages": [
                {"role": "system", "content": [{"text": system_prompt}]},
                {"role": "user", "content": [{"text": prompt}]}
            ]
        }
        
        # Guardrails integration (Future Step)
        # body["guardrailIdentifier"] = settings.guardrail_id
        # body["guardrailVersion"] = "DRAFT"

        response = bedrock_client.invoke(self.model_id, body)
        return response['output']['message']['content'][0]['text']

llm_service = LLMService()
```

### 1.3 Embedding Service (Titan V2)
**File:** `api/services/embedding_service.py`

Converts text into vectors using Titan Embeddings V2.

```python
from typing import List
from api.services.bedrock_service import bedrock_client

class EmbeddingService:
    def __init__(self, model_id="amazon.titan-embed-text-v2:0"):
        self.model_id = model_id

    def generate_embedding(self, text: str) -> List[float]:
        body = {
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        }
        response = bedrock_client.invoke(self.model_id, body)
        return response['embedding']

embedding_service = EmbeddingService()
```

---

## Part 2: Vector Database & Storage

### 2.1 Deploy ChromaDB (K8s)
**File:** `kubernetes/base/vectordb-deployment.yaml`

We deploy a single-node ChromaDB for the hybrid vector store.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vectordb
spec:
  serviceName: "vectordb"
  replicas: 1
  selector:
    matchLabels:
      app: vectordb
  template:
    metadata:
      labels:
        app: vectordb
    spec:
      containers:
      - name: chromadb
        image: chromadb/chroma:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: chroma-data
          mountPath: /chroma/chroma
  volumeClaimTemplates:
  - metadata:
      name: chroma-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vectordb-service
spec:
  selector:
    app: vectordb
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
```

### 2.2 Vector Store Service
**File:** `api/services/vector_store.py`

Manages connection to ChromaDB.

```python
import chromadb
from chromadb.config import Settings
from api.services.embedding_service import embedding_service

class VectorStore:
    def __init__(self, host="vectordb-service", port=8000):
        self.client = chromadb.HttpClient(
            host=host, 
            port=port,
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection("rag_docs")

    def add_documents(self, documents: list, metadatas: list, ids: list):
        # Generate embeddings in batch
        embeddings = [embedding_service.generate_embedding(doc) for doc in documents]
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, top_k=5, filter=None):
        query_embedding = embedding_service.generate_embedding(query)
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter
        )

vector_store = VectorStore()
```

---

## Part 3: Document Processing

### 3.1 Chunking Utility
**File:** `api/utils/chunking.py`

Splits text into manageable pieces for the LLM.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", " ", ""]
)

def chunk_text(text: str):
    return text_splitter.split_text(text)
```

### 3.2 Ingestion Service
**File:** `api/services/ingestion_service.py`

Orchestrates parsing, chunking, and indexing.

```python
import uuid
from api.utils.chunking import chunk_text
from api.services.vector_store import vector_store

async def ingest_document(filename: str, content: str, metadata: dict):
    chunks = chunk_text(content)
    
    ids = [f"{filename}_{i}" for i in range(len(chunks))]
    metadatas = [{**metadata, "chunk_index": i} for i in range(len(chunks))]
    
    vector_store.add_documents(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)
```

### 3.3 Document Upload Endpoint
**File:** `api/routers/documents.py`

```python
from fastapi import APIRouter, UploadFile, BackgroundTasks
from api.services.ingestion_service import ingest_document

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile, 
    background_tasks: BackgroundTasks,
    domain: str = "general"
):
    content = (await file.read()).decode("utf-8")
    
    # Process in background (async)
    background_tasks.add_task(
        ingest_document, 
        file.filename, 
        content, 
        {"domain": domain, "source": "web_upload"}
    )
    
    return {"status": "processing", "filename": file.filename}
```

### 3.4 GitHub Actions Data Sync
**File:** `.github/workflows/data-sync.yml`

Automated ingestion pipeline.

```yaml
name: Data Sync
on:
  push:
    paths:
      - 'data/documents/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Sync to API
        run: |
          # Use a script to loop through files and POST to API
          python3 scripts/sync_docs.py --url ${{ secrets.API_URL }} --dir data/documents
```

---

## Part 4: The RAG Pipeline

### 4.1 Retrieval & Generation Service
**File:** `api/services/rag_service.py`

Combines Retrieval (Vector Store) + Generation (LLM).

```python
from api.services.vector_store import vector_store
from api.services.llm_service import llm_service

class RAGService:
    def query(self, question: str, domain: str = None):
        # 1. Retrieve
        filters = {"domain": domain} if domain else None
        results = vector_store.search(question, top_k=3, filter=filters)
        
        context_chunks = results['documents'][0]
        context_text = "\n\n".join(context_chunks)
        
        # 2. Augment Prompt
        system_prompt = f"Answer using only the context below.\n\nContext:\n{context_text}"
        
        # 3. Generate
        answer = llm_service.generate_response(question, system_prompt)
        
        return {
            "question": question,
            "answer": answer,
            "sources": results['metadatas'][0]
        }

rag_service = RAGService()
```

### 4.2 Query Endpoint
**File:** `api/routers/query.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
from api.services.rag_service import rag_service

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    domain: str = None

@router.post("/query")
async def query_rag(request: QueryRequest):
    return rag_service.query(request.question, request.domain)
```

---

## Part 5: Domain Features & Frontend

### 5.1 Access Control Middleware
**File:** `api/dependencies.py`

Restrict queries to authorized domains only.

```python
from fastapi import Header, HTTPException
from typing import Annotated

async def verify_domain_access(
    x_user_role: Annotated[str, Header()] = "employee",
    domain: str = "general"
):
    # Simulating RBAC logic (replace with real DB check later)
    allowed_domains = {
        "admin": ["legal", "hr", "engineering", "general"],
        "employee": ["general", "engineering"],
        "intern": ["general"]
    }
    
    if domain and domain not in allowed_domains.get(x_user_role, []):
        raise HTTPException(status_code=403, detail=f"Role '{x_user_role}' cannot access domain '{domain}'")
    return True
```

### 5.2 Analytics Service
**File:** `api/services/analytics_service.py`

Track usage for governance.

```python
import time
import logging

logger = logging.getLogger("rag-analytics")
logging.basicConfig(level=logging.INFO)

class AnalyticsService:
    def track_query(self, domain: str, execution_time: float):
        entry = {
            "event": "query_executed",
            "domain": domain,
            "latency_ms": round(execution_time * 1000, 2),
            "timestamp": time.time()
        }
        logger.info(str(entry))

analytics = AnalyticsService()
```

### 5.3 Frontend UI Deployment
**File:** `kubernetes/base/frontend-deployment.yaml`

Deploy the frontend service.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rag-frontend
  template:
    metadata:
      labels:
        app: rag-frontend
    spec:
      containers:
      - name: ui
        image: llmops-rag-frontend:latest
        ports:
        - containerPort: 8501 # Streamlit default
        env:
        - name: API_URL
          value: "http://rag-api-service:80"
```

---

## Part 6: Verification

### 6.1 Manual Verification Steps

**1. Verify API Health**
```bash
curl http://localhost:8000/health
# Expect: {"status": "ok"}
```

**2. Test Document Ingestion**
```bash
curl -X POST "http://localhost:8000/documents/upload?domain=engineering" \
  -F "file=@./test_docs/deployment_guide.pdf"
# Expect: {"status": "processing", "filename": "deployment_guide.pdf"}
```

**3. Test RAG Query (General Domain)**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -H "x-user-role: employee" \
  -d '{"question": "How do I deploy to EKS?", "domain": "engineering"}'
# Expect: {"answer": "...", "sources": [...]}
```

**4. Verify Access Control (Negative Test)**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -H "x-user-role: intern" \
  -d '{"question": "What is the engineering budget?", "domain": "engineering"}'
# Expect: 403 Forbidden
```

**5. Python Connectivity Test**
Create `scripts/test_rag.py`:
```python
import requests

def test_full_flow():
    # 1. Upload
    files = {'file': open('data/sample.txt', 'rb')}
    up_res = requests.post("http://localhost:8000/documents/upload", files=files)
    assert up_res.status_code == 200
    print("✅ Upload Success")

    # 2. Query
    payload = {"question": "summarize sample", "domain": "general"}
    q_res = requests.post("http://localhost:8000/query", json=payload)
    assert q_res.status_code == 200
    print("✅ Query Response:", q_res.json()['answer'])

if __name__ == "__main__":
    test_full_flow()
```

### 6.2 Verification Checklist

### ✅ Bedrock Integration
- [ ] Connect `boto3` to Bedrock.
- [ ] Generate an embedding vector -> `[0.1, ... 0.9]`.
- [ ] Generate an LLM response -> "Hello world".

### ✅ Vector Database
- [ ] Deploy ChromaDB to Minikube.
- [ ] Ingest a test document via API.
- [ ] Search for "test" and see it hit the correct chunk.

### ✅ RAG Pipeline
- [ ] Upload a file (e.g., "policy.pdf").
- [ ] Ask a question about the policy.
- [ ] Verify the answer cites the policy file.
- [ ] Verify `rag-analytics` logs show the query event.

### ✅ Domain Controls
- [ ] Set header `x-user-role: intern`.
- [ ] Ask a question in `domain: legal`.
- [ ] Verify `403 Forbidden` response.
