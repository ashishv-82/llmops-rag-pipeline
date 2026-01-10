# Phase 7: Basic UI Frontend (Streamlit) - Implementation Plan

**Goal:** Implement a lightweight, developer-focused frontend using Streamlit to provide immediate visual interaction capabilities (Chat & Upload) for the RAG system, facilitating rapid testing and demonstration.

---

## 🏗️ Architectural Context

Phase 7 bridges the gap between the purely API-based backend and the future full-scale React application. It introduces **Visual Interactivity** through:
1.  **Immediate Feedback Loop**: Enabling developers to test chat responses and document uploads visually.
2.  **Role Simulation**: Testing RBAC logic without complex auth providers.
3.  **Deployment Verification**: Validating the full EKS stack from a user's perspective.

**Engineering Outcomes:**
- **Visual Interface**: A deployed Streamlit application accessible via HTTP.
- **Document Ingestion**: Drag-and-drop upload functionality integrated with the S3/API pipeline.
- **Interactive Querying**: Functional chat interface with source attribution display.
- **Infrastructure Maturity**: Expansion of the EKS stack to include frontend services and ECR repositories.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Frontend Application](#part-1-frontend-application)**
- [1.1 Streamlit App Logic](#11-streamlit-app-logic)
- [1.2 Containerization](#12-containerization)

**[Part 2: Infrastructure Setup](#part-2-infrastructure-setup)**
- [2.1 ECR Repository](#21-ecr-repository)
- [2.2 Kubernetes Deployment](#22-kubernetes-deployment)

**[Part 3: Verification](#part-3-verification)**
- [3.1 Local Testing](#31-local-testing)
- [3.2 Production Verification](#32-production-verification)

---

## Prerequisites

- **Phase 6 Complete**: API and MLOps features operational.
- **Terraform State**: Production state file initialized.
- **Docker**: Installed locally for building the frontend image.

---

## Part 1: Frontend Application

### 1.1 Streamlit App Logic
**File:** `frontend/app.py`

The application serves as the user interface, managing API communication for uploading files and querying the RAG system.

```python
import streamlit as st
import requests
import os

# API endpoint configuration
API_URL = os.getenv("API_URL", "http://rag-api-service:80")

st.set_page_config(page_title="RAG Document Q&A", layout="wide")
st.title("🔍 RAG Document Q&A System")

# Sidebar for RBAC Simulation
with st.sidebar:
    st.header("Settings")
    domain = st.selectbox("Select Domain", ["general", "legal", "hr", "engineering"])
    user_role = st.selectbox("Your Role", ["admin", "employee", "intern"])

# Document Upload Section
st.header("📤 Upload Documents")
uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'txt', 'docx'])
if uploaded_file and st.button("Upload"):
    with st.spinner("Uploading..."):
        files = {'file': uploaded_file}
        params = {'domain': domain}
        try:
            response = requests.post(f"{API_URL}/documents/upload", files=files, params=params)
            if response.status_code == 200:
                st.success(f"✅ {uploaded_file.name} uploaded successfully!")
            else:
                st.error(f"❌ Upload failed: {response.text}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Chat Interface
st.header("💬 Ask Questions")
question = st.text_input("Enter your question")

if st.button("Search", type="primary"):
    with st.spinner("Searching..."):
        try:
            response = requests.post(
                f"{API_URL}/query",
                json={"question": question, "domain": domain},
                headers={"x-user-role": user_role}
            )
            if response.status_code == 200:
                result = response.json()
                st.subheader("Answer")
                st.write(result['answer'])
                
                # Display Metrics and Sources
                col1, col2 = st.columns(2)
                col1.metric("Domain", result.get('domain', 'N/A'))
                col2.metric("Time", f"{result.get('execution_time_ms', 0)}ms")
                
                with st.expander("📚 Sources"):
                    st.json(result.get('sources', []))
            else:
                st.error(f"❌ Query failed: {response.text}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
```

### 1.2 Containerization
**File:** `frontend/Dockerfile`

Standard Python container optimized for Streamlit.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 1.3 Data Seeding (Local Development)
**File:** `scripts/seed_data.py`

A utility script to populate the local Vector DB with Documents (e.g., Vietnam War PDF) for immediately verifying the UI.

```python
#!/usr/bin/env python3
import requests
import sys
import os
import time
import argparse
from pathlib import Path

def wait_for_api(api_url: str, timeout: int = 60):
    """Block until API is healthy"""
    print(f"⏳ Waiting for API at {api_url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{api_url}/health")
            if response.status_code == 200:
                print("✅ API is ready!")
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    
    print("❌ API failed to become ready.")
    sys.exit(1)

def seed_data(file_path: str, domain: str = "history", api_url: str = "http://localhost:8000"):
    """Upload document to RAG API"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
        
    print(f"📤 Seeding data from {path.name} (Domain: {domain})...")
    
    with open(path, 'rb') as f:
        files = {'file': (path.name, f, 'application/pdf')}
        params = {'domain': domain}
        
        try:
            response = requests.post(f"{api_url}/documents/upload", files=files, params=params)
            
            if response.status_code == 200:
                print(f"✅ Successfully ingested {path.name}!")
                print(f"👉 S3 Key: {response.json().get('s3_key')}")
                print(f"👉 Status: {response.json().get('status')}")
            else:
                print(f"❌ Upload failed: {response.text}")
                sys.exit(1)
        
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed RAG with initial documents")
    parser.add_argument("file_path", help="Path to PDF/TXT file to upload")
    parser.add_argument("--domain", default="history", help="Domain tag for the document")
    parser.add_argument("--url", default="http://localhost:8000", help="API URL")
    
    args = parser.parse_args()
    
    wait_for_api(args.url)
    seed_data(args.file_path, args.domain, args.url)
```

**Usage:**
```bash
python3 scripts/seed_data.py "data/documents/history/The_Vietnam_War_v2.pdf" --domain history
```

---

## Part 2: Infrastructure Setup

### 2.1 ECR Repository
**File:** `terraform/environments/prod/main.tf`

A dedicated Elastic Container Registry (ECR) repository is provisioned to store the frontend images securely.

```hcl
module "ecr_frontend" {
  source = "../../modules/ecr"

  repository_name      = "llmops-rag-frontend"
  image_tag_mutability = "MUTABLE"
  scan_on_push         = true
  encryption_type      = "AES256"

  tags = {
    Environment = "prod"
  }
}
```

### 2.2 Kubernetes Deployment
**File:** `kubernetes/base/frontend-deployment.yaml`

Deploys the container to the EKS cluster.
- **Deployment**: Single replica (stateless).
- **Service**: ClusterIP service mapping port 80 -> 8501.
- **Environment**: Injects `API_URL: http://rag-api-service:80` to ensure internal cluster communication.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-frontend
  namespace: prod
  labels:
    app: rag-frontend
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
      - name: rag-frontend
        image: 152141418178.dkr.ecr.ap-southeast-2.amazonaws.com/llmops-rag-frontend:latest
        ports:
        - containerPort: 8501
        env:
        - name: API_URL
          value: "http://rag-api-service:80"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: rag-frontend-service
  namespace: prod
spec:
  selector:
    app: rag-frontend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8501
  type: ClusterIP
```

---

## Part 3: Verification

### 3.1 Local Testing
Validate the UI logic before deployment.

```bash
cd frontend
pip install -r requirements.txt
export API_URL="http://localhost:8000"
streamlit run app.py
```
*   **Success Criteria**: App opens at `localhost:8501`, Chat returns answers from local API.

### 3.2 Production Verification
Validate the full deployment chain.

1.  **Infra Apply**: `terraform apply` (creates ECR).
2.  **Build & Push**: Docker build and push to new ECR repo.
3.  **Deploy**: `./scripts/deploy_to_eks.sh prod`.
4.  **Access**: `kubectl port-forward svc/rag-frontend-service -n prod 8501:80`.
5.  **Test**: Upload a file and verify it appears in the system.

*   **Success Criteria**: "✅ Upload successful" message in UI confirmed by log entry in API pod.
