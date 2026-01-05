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
- [1.4 Configure Bedrock Guardrails](#14-configure-bedrock-guardrails)

**[Part 2: Vector Database & Storage](#part-2-vector-database--storage)**
- [2.1 Deploy ChromaDB (K8s)](#21-deploy-chromadb-k8s)
- [2.2 Vector Store Service](#22-vector-store-service)

**[Part 3: Document Processing](#part-3-document-processing)**
- [3.1 Chunking Utility](#31-chunking-utility)
- [3.2 Ingestion Service](#32-ingestion-service)
- [3.3 Document Upload Endpoint](#33-document-upload-endpoint)
- [3.3.1 S3 Service](#331-s3-service)
- [3.4 GitHub Actions Data Sync](#34-github-actions-data-sync)

**[Part 4: The RAG Pipeline](#part-4-the-rag-pipeline)**
- [4.1 Domain-Aware Prompt Templates](#41-domain-aware-prompt-templates)
- [4.2 Retrieval & Generation Service](#42-retrieval--generation-service)
- [4.3 Query Endpoint](#43-query-endpoint)

**[Part 5: Domain Features & Frontend](#part-5-domain-features--frontend)**
- [5.1 Access Control Middleware](#51-access-control-middleware)
- [5.2 Analytics Service](#52-analytics-service)
- [5.3 Frontend UI Deployment](#53-frontend-ui-deployment)

**[Part 6: Verification](#part-6-verification)**
- [6.1 Manual Verification Steps](#61-manual-verification-steps)
- [6.2 Verification Checklist](#62-verification-checklist)

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

Handles text generation with Amazon Nova 2 and Bedrock Guardrails.

```python
from api.services.bedrock_service import bedrock_client
from api.config import settings

class LLMService:
    def __init__(self, model_id="amazon.nova-2-lite-v1:0"):
        self.model_id = model_id
        self.use_guardrails = hasattr(settings, 'guardrail_id')

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        body = {
            "inferenceConfig": {"max_new_tokens": 1000},
            "messages": [
                {"role": "system", "content": [{"text": system_prompt}]},
                {"role": "user", "content": [{"text": prompt}]}
            ]
        }
        
        # Guardrails integration for PII masking and content filtering
        if self.use_guardrails:
            body["guardrailIdentifier"] = settings.guardrail_id
            body["guardrailVersion"] = "DRAFT"

        response = bedrock_client.invoke(self.model_id, body)
        return response['output']['message']['content'][0]['text']

llm_service = LLMService()
```

### 1.4 Configure Bedrock Guardrails
**File:** `scripts/setup_guardrails.py`

Create guardrails via AWS Console or CLI:

```python
import boto3

def create_guardrail():
    client = boto3.client('bedrock', region_name='ap-southeast-2')
    
    response = client.create_guardrail(
        name='rag-content-filter',
        description='PII masking and content filtering for RAG',
        contentPolicyConfig={
            'filtersConfig': [
                {'type': 'SEXUAL', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
                {'type': 'VIOLENCE', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
                {'type': 'HATE', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
                {'type': 'INSULTS', 'inputStrength': 'MEDIUM', 'outputStrength': 'MEDIUM'},
            ]
        },
        sensitiveInformationPolicyConfig={
            'piiEntitiesConfig': [
                {'type': 'EMAIL', 'action': 'ANONYMIZE'},
                {'type': 'PHONE', 'action': 'ANONYMIZE'},
                {'type': 'SSN', 'action': 'BLOCK'},
            ]
        },
        topicPolicyConfig={
            'topicsConfig': [
                {
                    'name': 'Financial Advice',
                    'definition': 'Investment or financial planning advice',
                    'type': 'DENY'
                }
            ]
        }
    )
    
    print(f"Guardrail created: {response['guardrailId']}")
    print(f"Add to .env: GUARDRAIL_ID={response['guardrailId']}")

if __name__ == "__main__":
    create_guardrail()
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

Manages connection to ChromaDB with hybrid search (vector + BM25).

```python
import chromadb
from chromadb.config import Settings
from api.services.embedding_service import embedding_service
from rank_bm25 import BM25Okapi
import numpy as np

class VectorStore:
    def __init__(self, host="vectordb-service", port=8000):
        self.client = chromadb.HttpClient(
            host=host, 
            port=port,
            settings=Settings(allow_reset=True)
        )
        self.collection = self.client.get_or_create_collection("rag_docs")
        self.bm25 = None
        self.documents_cache = []
    
    def add_documents(self, documents: list, metadatas: list, ids: list):
        # Generate embeddings in batch
        embeddings = [embedding_service.generate_embedding(doc) for doc in documents]
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        # Update BM25 index
        self._rebuild_bm25_index()
    
    def _rebuild_bm25_index(self):
        """Rebuild BM25 index from all documents"""
        all_docs = self.collection.get()
        self.documents_cache = all_docs['documents']
        tokenized_docs = [doc.lower().split() for doc in self.documents_cache]
        self.bm25 = BM25Okapi(tokenized_docs)
    
    def hybrid_search(self, query: str, top_k=5, filter=None, alpha=0.5):
        """
        Hybrid search combining vector similarity and BM25.
        alpha: weight for vector search (1-alpha for BM25)
        """
        # Vector search
        query_embedding = embedding_service.generate_embedding(query)
        vector_results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get more candidates
            where=filter
        )
        
        # BM25 search
        if self.bm25 is None:
            self._rebuild_bm25_index()
        
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Combine scores using Reciprocal Rank Fusion
        combined_scores = {}
        
        # Add vector scores
        for idx, (doc_id, distance) in enumerate(zip(
            vector_results['ids'][0], 
            vector_results['distances'][0]
        )):
            # Convert distance to similarity (lower is better)
            similarity = 1 / (1 + distance)
            combined_scores[doc_id] = alpha * similarity
        
        # Add BM25 scores
        for idx, (doc_id, score) in enumerate(zip(
            vector_results['ids'][0],
            bm25_scores
        )):
            if doc_id in combined_scores:
                combined_scores[doc_id] += (1 - alpha) * score
        
        # Sort and return top_k
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Fetch full results
        final_ids = [doc_id for doc_id, _ in sorted_ids]
        return self.collection.get(ids=final_ids)
    
    def search(self, query: str, top_k=5, filter=None):
        """Fallback to vector-only search"""
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
from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException
from api.services.ingestion_service import ingest_document
from api.services.s3_service import s3_service
import PyPDF2
import io

router = APIRouter()

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file: UploadFile) -> None:
    """Validate file type and size"""
    # Check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        )
    
    # Check size (FastAPI doesn't provide size directly, check in memory)
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

def parse_document(file: UploadFile, content_bytes: bytes) -> str:
    """Parse document based on file type"""
    ext = file.filename.split('.')[-1].lower()
    
    if ext == 'txt':
        return content_bytes.decode('utf-8')
    
    elif ext == 'pdf':
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    elif ext == 'docx':
        # TODO: Implement DOCX parsing with python-docx
        raise HTTPException(status_code=501, detail="DOCX parsing not yet implemented")
    
    return ""

@router.post("/upload")
async def upload_document(
    file: UploadFile, 
    background_tasks: BackgroundTasks,
    domain: str = "general"
):
    # Validate file
    validate_file(file)
    
    # Read content
    content_bytes = await file.read()
    
    # Parse document
    text_content = parse_document(file, content_bytes)
    
    # Upload to S3
    s3_key = f"documents/{domain}/{file.filename}"
    s3_service.upload_file(content_bytes, s3_key)
    
    # Process in background (async)
    background_tasks.add_task(
        ingest_document, 
        file.filename, 
        text_content, 
        {
            "domain": domain, 
            "source": "web_upload",
            "s3_key": s3_key
        }
    )
    
    return {
        "status": "processing", 
        "filename": file.filename,
        "s3_key": s3_key
    }
```

### 3.3.1 S3 Service
**File:** `api/services/s3_service.py`

```python
import boto3
from api.config import settings

class S3Service:
    def __init__(self):
        self.client = boto3.client('s3', region_name=settings.aws_region)
        self.bucket = settings.documents_bucket
    
    def upload_file(self, content: bytes, key: str):
        """Upload file to S3"""
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content
        )
    
    def download_file(self, key: str) -> bytes:
        """Download file from S3"""
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key
        )
        return response['Body'].read()

s3_service = S3Service()
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

### 4.1 Domain-Aware Prompt Templates
**File:** `api/prompts/templates.py`

Different domains require different response styles.

```python
DOMAIN_PROMPTS = {
    "legal": {
        "system": """You are a legal document assistant. Provide precise, citation-based answers.
Always reference specific sections or clauses. Use formal legal terminology.
If uncertain, state limitations clearly.""",
        "user_template": """Based on the following legal documents:

{context}

Question: {question}

Provide a detailed answer with specific citations."""
    },
    "hr": {
        "system": """You are an HR policy assistant. Provide clear, empathetic guidance.
Focus on employee welfare and company policy compliance.
Use accessible language.""",
        "user_template": """Based on the following HR policies:

{context}

Question: {question}

Provide a helpful, policy-compliant answer."""
    },
    "engineering": {
        "system": """You are a technical documentation assistant. Provide accurate, actionable guidance.
Include code examples when relevant. Focus on best practices.""",
        "user_template": """Based on the following technical documentation:

{context}

Question: {question}

Provide a technical answer with examples if applicable."""
    },
    "general": {
        "system": """You are a helpful assistant. Answer questions based on the provided context.
Be concise and accurate.""",
        "user_template": """Context:

{context}

Question: {question}

Answer:"""
    }
}

def get_prompt(domain: str, context: str, question: str) -> tuple[str, str]:
    """Get system and user prompts for a domain"""
    template = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])
    system_prompt = template["system"]
    user_prompt = template["user_template"].format(context=context, question=question)
    return system_prompt, user_prompt
```

### 4.2 Retrieval & Generation Service
**File:** `api/services/rag_service.py`

Combines Retrieval (Vector Store) + Generation (LLM) with domain awareness.

```python
from api.services.vector_store import vector_store
from api.services.llm_service import llm_service
from api.prompts.templates import get_prompt
import time

class RAGService:
    def query(self, question: str, domain: str = None, use_hybrid=True):
        start_time = time.time()
        
        # 1. Retrieve with hybrid search
        filters = {"domain": domain} if domain else None
        
        if use_hybrid:
            results = vector_store.hybrid_search(
                question, 
                top_k=3, 
                filter=filters,
                alpha=0.7  # 70% vector, 30% BM25
            )
        else:
            results = vector_store.search(question, top_k=3, filter=filters)
        
        context_chunks = results['documents']
        context_text = "\n\n".join(context_chunks)
        
        # 2. Get domain-specific prompts
        system_prompt, user_prompt = get_prompt(
            domain or "general",
            context_text,
            question
        )
        
        # 3. Generate with guardrails
        answer = llm_service.generate_response(user_prompt, system_prompt)
        
        execution_time = time.time() - start_time
        
        return {
            "question": question,
            "answer": answer,
            "sources": results['metadatas'],
            "domain": domain,
            "execution_time_ms": round(execution_time * 1000, 2)
        }

rag_service = RAGService()
```

### 4.3 Query Endpoint
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
**File:** `frontend/app.py`

Simple Streamlit UI for document upload and querying.

```python
import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://rag-api-service:80")

st.set_page_config(page_title="RAG Document Q&A", layout="wide")

st.title("🔍 RAG Document Q&A System")

# Sidebar for domain selection
with st.sidebar:
    st.header("Settings")
    domain = st.selectbox(
        "Select Domain",
        ["general", "legal", "hr", "engineering"],
        help="Filter documents by domain"
    )
    
    user_role = st.selectbox(
        "Your Role",
        ["admin", "employee", "intern"],
        help="Determines access permissions"
    )

# Document Upload Section
st.header("📤 Upload Documents")
with st.expander("Upload a new document"):
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'txt', 'docx'],
        help="Upload PDF, TXT, or DOCX files"
    )
    
    if uploaded_file and st.button("Upload"):
        with st.spinner("Uploading..."):
            files = {'file': uploaded_file}
            params = {'domain': domain}
            
            try:
                response = requests.post(
                    f"{API_URL}/documents/upload",
                    files=files,
                    params=params
                )
                
                if response.status_code == 200:
                    st.success(f"✅ {uploaded_file.name} uploaded successfully!")
                    st.json(response.json())
                else:
                    st.error(f"❌ Upload failed: {response.text}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Query Section
st.header("💬 Ask Questions")
question = st.text_input(
    "Enter your question",
    placeholder="e.g., What is the deployment process?"
)

if st.button("Search", type="primary"):
    if not question:
        st.warning("Please enter a question")
    else:
        with st.spinner("Searching..."):
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": question, "domain": domain},
                    headers={"x-user-role": user_role}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display answer
                    st.subheader("Answer")
                    st.write(result['answer'])
                    
                    # Display metadata
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Domain", result.get('domain', 'N/A'))
                    with col2:
                        st.metric("Response Time", f"{result.get('execution_time_ms', 0)}ms")
                    
                    # Display sources
                    with st.expander("📚 Sources"):
                        for idx, source in enumerate(result.get('sources', [])):
                            st.write(f"**Source {idx+1}:**")
                            st.json(source)
                
                elif response.status_code == 403:
                    st.error("🚫 Access Denied: You don't have permission to access this domain")
                else:
                    st.error(f"❌ Query failed: {response.text}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
```

**File:** `frontend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**File:** `frontend/requirements.txt`

```
streamlit==1.29.0
requests==2.31.0
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
