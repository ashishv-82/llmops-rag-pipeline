# Phase 5: Monitoring & Observability - Implementation Plan

**Goal:** Instrument the RAG application with comprehensive monitoring, cost tracking, and alerting to ensure production reliability and cost governance. We will use **Terraform** and **Helm** to deploy a production-grade monitoring stack.

---

## 🏗️ Architectural Context

Phase 5 establishes **Observability Excellence** through:
1.  **Infrastructure as Code**: Deploying Prometheus/Grafana stack via Terraform.
2.  **Metrics Collection**: Prometheus scraping application and infrastructure metrics.
3.  **Visualization**: Grafana dashboards for cost, performance, and health monitoring.
4.  **Application Instrumentation**: Custom metrics for LLM token usage and RAG latency.

**Engineering Outcomes:**
- **Production Stack**: `kube-prometheus-stack` deployed via Helm triggers standard best practices (AlertManager, NodeExporter, KubeStateMetrics).
- **FinOps Visibility**: Real-time cost dashboards.
- **Proactive Alerting**: Automated notifications for budget overruns.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Infrastructure (Terraform & Helm)](#part-1-infrastructure-terraform--helm)**
- [1.1 Monitoring Module](#11-monitoring-module)
- [1.2 Terraform Configuration](#12-terraform-configuration)
- [1.3 Apply Infrastructure](#13-apply-infrastructure)

**[Part 2: Application Instrumentation](#part-2-application-instrumentation)**
- [2.1 Metrics Library Setup](#21-metrics-library-setup)
- [2.2 Request Latency & Errors](#22-request-latency--errors)
- [2.3 LLM Cost Tracking](#23-llm-cost-tracking)

**[Part 3: Visualization & Alerting](#part-3-visualization--alerting)**
- [3.1 Accessing Grafana](#31-accessing-grafana)
- [3.2 Custom Dashboards](#32-custom-dashboards)
- [3.3 Alerting Rules](#33-alerting-rules)

**[Part 4: Verification](#part-4-verification)**

---

## Prerequisites

- **Phase 4 Complete**: CI/CD pipelines operational.
- **Kubernetes Cluster**: Running (Minikube or EKS).
- **Terraform**: Installed and initialized.
- **Helm**: Installed (required for local verification).

---

## Part 1: Infrastructure (Terraform & Helm)

We will use the `helm_release` resource in Terraform to deploy the `kube-prometheus-stack` chart.

### 1.1 Monitoring Module

**File:** `terraform/modules/monitoring/main.tf`

```hcl
terraform {
  required_providers {
    helm = {
      source  = "hashicorp/helm"
    }
  }
}

resource "helm_release" "kube_prometheus_stack" {
  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  namespace        = var.namespace
  create_namespace = true
  version          = "56.0.0"

  values = [
    file("${path.module}/values.yaml")
  ]

  set = [
    {
      name  = "grafana.adminPassword"
      value = var.grafana_password
    },
    {
      name  = "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues"
      value = "false"
    },
    {
      name  = "grafana.service.type"
      value = "LoadBalancer"
    }
  ]
}
```

**File:** `terraform/modules/monitoring/variables.tf`

```hcl
variable "namespace" {
  description = "Namespace to deploy monitoring stack"
  type        = string
  default     = "monitoring"
}

variable "grafana_password" {
  description = "Admin password for Grafana"
  type        = string
  sensitive   = true
}
```

**File:** `terraform/modules/monitoring/outputs.tf`

```hcl
output "grafana_admin_password" {
  description = "The admin password for Grafana (sensitive)"
  value       = var.grafana_password
  sensitive   = true
}

output "namespace" {
  description = "The namespace where the monitoring stack is deployed"
  value       = var.namespace
}
```

**File:** `terraform/modules/monitoring/values.yaml`

```yaml
grafana:
  service:
    type: LoadBalancer

prometheus:
  prometheusSpec:
    scrapeInterval: "15s"
    resources:
      requests:
        memory: 400Mi
      limits:
        memory: 1Gi

alertmanager:
  enabled: true
```

### 1.2 Terraform Configuration

**File:** `terraform/environments/dev/providers.tf`

```hcl
provider "aws" {
  region = "ap-southeast-2"
}

provider "helm" {
  kubernetes = {
    config_path = "~/.kube/config"
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}
```

**File:** `terraform/environments/dev/main.tf`

```hcl
module "monitoring" {
  source           = "../../modules/monitoring"
  namespace        = "monitoring"
  grafana_password = "admin" # Change for real environments!
}
```

### 1.3 Integration & Deployment

```bash
cd terraform/environments/dev
terraform init
terraform apply -auto-approve
```

**Immediate Verification:**

1.  **Check Pods:**
    ```bash
    kubectl get pods -n monitoring
    # Wait until all pods are 'Running'
    ```

2.  **Access Grafana:**
    ```bash
    kubectl port-forward svc/prometheus-grafana 3200:80 -n monitoring
    ```
    - Open [http://localhost:3200](http://localhost:3200)
    - Login: `admin` / `admin`

---

## Part 2: Application Instrumentation

We will use `prometheus-fastapi-instrumentator` to automatically expose metrics from our API.

### 2.1 Metrics Library Setup

**File:** `api/requirements.txt`
```text
prometheus-fastapi-instrumentator==7.0.0
prometheus-client==0.19.0
```

**Install:**
```bash
pip install -r api/requirements.txt
```

**File:** `api/main.py`
```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

# Initialize Instrumentator
instrumentator = Instrumentator().instrument(app)

@app.on_event("startup")
async def _startup():
    instrumentator.expose(app)
```

### 2.2 Request Latency & Errors

The instrumentator automatically tracks:
- `http_requests_total`
- `http_request_duration_seconds`
- `http_requests_created`

No custom code needed for basic RED metrics (Rate, Errors, Duration).

### 2.3 LLM Cost Tracking

**File:** `api/utils/metrics.py`

We need custom metrics for business logic.

```python
from prometheus_client import Counter, Histogram

# Metric Definitions
RAG_COST_TOTAL = Counter(
    "rag_cost_dollars_total",
    "Total estimated cost of RAG pipeline in USD",
    ["model", "environment"]
)

RAG_TOKEN_USAGE = Counter(
    "rag_token_usage_total",
    "Total token usage by model type",
    ["model", "type", "environment"]
)

RAG_REQUEST_LATENCY = Histogram(
    "rag_request_duration_seconds",
    "Time spent processing RAG requests",
    ["stage", "environment"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
)

def track_cost(amount: float, model: str, env: str = "dev"):
    """Increment the cost counter."""
    RAG_COST_TOTAL.labels(model=model, environment=env).inc(amount)

def track_tokens(count: int, model: str, type: str, env: str = "dev"):
    """Increment token usage (input/output)."""
    RAG_TOKEN_USAGE.labels(model=model, type=type, environment=env).inc(count)
```

### 2.4 Verify Locally

Before deploying, verify the metrics endpoint is active:

1.  **Run API Locally:**
    ```bash
    uvicorn api.main:app --port 8000
    ```

2.  **Check Metrics:**
    ```bash
    curl http://localhost:8000/metrics
    ```
    *Expect to see output starting with:*
    ```text
    # HELP python_gc_objects_collected_total Objects collected during gc
    # TYPE python_gc_objects_collected_total counter
    ...
    # HELP rag_cost_dollars_total Total estimated cost of RAG pipeline in USD
    # TYPE rag_cost_dollars_total counter
    ```

3.  **Cleanup:**
    - Stop the local server by pressing `Ctrl+C`.

### 2.5 Deploy New Version (Minikube)

Since we modified the code, we must rebuild the image **inside** Minikube's Docker daemon and restart the pod.

1.  **Configure Shell:**
    ```bash
    eval $(minikube docker-env)
    ```

2.  **Rebuild Image:**
    ```bash
    docker build -t llmops-rag-api:latest -f api/Dockerfile .
    ```

3.  **Restart Pod:**
    ```bash
    kubectl rollout restart deployment/rag-api -n dev
    ```

### 2.6 Verify In-Cluster (Production Check)

To be 100% sure the Pod is serving metrics inside the cluster network:

1.  **Get Pod Name:**
    ```bash
    kubectl get pods -n dev
    ```

2.  **Curl from Inside:**
    ```bash
    kubectl exec -n dev [POD_NAME] -- curl -s http://localhost:8000/metrics | head -n 10
    ```
    *Expect to see output starting with:*
    ```text
    # HELP python_gc_objects_collected_total Objects collected during gc
    # TYPE python_gc_objects_collected_total counter
    python_gc_objects_collected_total{generation="0"} 234.0
    ...
    ```


### 2.7 Enable Prometheus Scraping (ServiceMonitor)

**Architecture Note:** This step connects your API to Prometheus. The ServiceMonitor lives in `kubernetes/dev/` (not Terraform) because it's application-specific configuration, while the monitoring infrastructure (Prometheus/Grafana) is managed by Terraform.

**File:** `kubernetes/dev/servicemonitor.yaml`

```yaml
# Creates a Service to expose metrics port
apiVersion: v1
kind: Service
metadata:
  name: rag-api-metrics
  namespace: dev
  labels:
    app: rag-api
spec:
  selector:
    app: rag-api
  ports:
    - name: metrics
      port: 8000
      targetPort: 8000
---
# Tells Prometheus Operator to scrape this service
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: rag-api
  namespace: dev
  labels:
    app: rag-api
spec:
  selector:
    matchLabels:
      app: rag-api
  endpoints:
    - port: metrics
      path: /metrics
      interval: 15s
```

**Deploy:**
```bash
kubectl apply -f kubernetes/dev/servicemonitor.yaml
```

**Verify Prometheus is Scraping:**
```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Open http://localhost:9090/targets
# Look for "dev/rag-api/0" - status should be "UP"
```

### 2.8 Integrate Metrics into RAG Code

Now that the metrics infrastructure is ready, we need to **call** the tracking functions in our actual RAG pipeline.

#### 2.8.1 Understanding the Integration Points

The metrics need to be tracked at three key points:

1. **Query Endpoint** (`api/routers/query.py`) - Track overall latency
2. **RAG Service** (`api/services/rag_service.py`) - Track cost and tokens
3. **LLM Calls** - Capture actual usage from API responses

#### 2.8.2 Modify Query Router

**File:** `api/routers/query.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
from api.services.rag_service import rag_service
from api.utils.metrics import RAG_REQUEST_LATENCY
import time

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    domain: str | None = None

@router.post("/query")
async def query_rag(request: QueryRequest):
    # Start timing the entire request
    start_time = time.time()
    
    try:
        # Call RAG service
        result = rag_service.query(request.question, request.domain)
        
        # Record total latency
        duration = time.time() - start_time
        RAG_REQUEST_LATENCY.labels(
            stage="total", 
            environment="dev"
        ).observe(duration)
        
        return result
    except Exception as e:
        # Still record latency even on failure
        duration = time.time() - start_time
        RAG_REQUEST_LATENCY.labels(
            stage="total_error", 
            environment="dev"
        ).observe(duration)
        raise
```

#### 2.8.3 Modify RAG Service

**File:** `api/services/rag_service.py`

Add metrics tracking after LLM calls:

```python
from api.utils.metrics import track_cost, track_tokens, RAG_REQUEST_LATENCY
import time

class RAGService:
    def query(self, question: str, domain: str = None):
        # ... existing retrieval code ...
        
        # Track retrieval latency
        retrieval_start = time.time()
        context = self.retrieve_context(question, domain)
        retrieval_duration = time.time() - retrieval_start
        RAG_REQUEST_LATENCY.labels(
            stage="retrieval", 
            environment="dev"
        ).observe(retrieval_duration)
        
        # Track generation latency
        generation_start = time.time()
        response = self.generate_response(question, context)
        generation_duration = time.time() - generation_start
        RAG_REQUEST_LATENCY.labels(
            stage="generation", 
            environment="dev"
        ).observe(generation_duration)
        
        # Track cost and tokens (example values - replace with actual)
        # You'll need to extract these from the LLM response
        track_cost(0.0015, model="bedrock-nova", env="dev")
        track_tokens(150, model="bedrock-nova", type="input", env="dev")
        track_tokens(300, model="bedrock-nova", type="output", env="dev")
        
        return response
```

#### 2.8.4 Extract Real Token Counts

To track **actual** token usage, you need to parse the LLM response metadata:

```python
# Example for Bedrock
response = bedrock_client.invoke_model(...)
response_body = json.loads(response['body'].read())

# Extract token counts from response
input_tokens = response_body.get('usage', {}).get('input_tokens', 0)
output_tokens = response_body.get('usage', {}).get('output_tokens', 0)

# Track actual usage
track_tokens(input_tokens, model="bedrock-nova", type="input", env="dev")
track_tokens(output_tokens, model="bedrock-nova", type="output", env="dev")

# Calculate cost (example pricing)
cost = (input_tokens * 0.000008) + (output_tokens * 0.000024)
track_cost(cost, model="bedrock-nova", env="dev")
```

#### 2.8.5 Test the Integration

1. **Rebuild and Deploy:**
   ```bash
   eval $(minikube docker-env)
   docker build -t llmops-rag-api:latest -f api/Dockerfile .
   kubectl rollout restart deployment/rag-api -n dev
   ```

2. **Make a Test Request:**
   ```bash
   curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What is RAG?", "domain": null}'
   ```

3. **Check Metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep rag_
   ```
   
   *Expected output:*
   ```text
   rag_cost_dollars_total{environment="dev",model="bedrock-nova"} 0.0015
   rag_token_usage_total{environment="dev",model="bedrock-nova",type="input"} 150.0
   rag_token_usage_total{environment="dev",model="bedrock-nova",type="output"} 300.0
   rag_request_duration_seconds_bucket{environment="dev",stage="total",le="0.1"} 0.0
   ```

4. **Verify in Grafana:**
   - Open http://localhost:3200
   - Navigate to "RAG API Metrics" dashboard
   - You should now see data in the graphs! 📈

---


## Part 3: Visualization & Alerting

### 3.1 Accessing Grafana

Since we deployed via Helm with LoadBalancer (or NodePort):

```bash
# Get Grafana Service URL
minikube service prometheus-grafana -n monitoring --url
```

Login: `admin` / `admin` (or whatever var.grafana_password was set to).

### 3.2 Custom Dashboards

We will create a "GenAI Cost" Dashboard JSON.

1.  **Create JSON File:** `terraform/modules/monitoring/dashboards/rag_metrics.json`
    
    This file is the "Source of Truth" for our dashboard. Save the following content:

    ```json
    {
      "annotations": { "list": [ { "builtIn": 1, "datasource": { "type": "grafana", "uid": "-- Grafana --" }, "enable": true, "hide": true, "iconColor": "rgba(0, 211, 255, 1)", "name": "Annotations & Alerts", "type": "dashboard" } ] },
      "editable": true,
      "fiscalYearStartMonth": 0,
      "graphTooltip": 0,
      "id": null,
      "links": [],
      "liveNow": false,
      "panels": [
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": { "defaults": { "color": { "mode": "palette-classic" }, "custom": { "axisCenteredZero": false, "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto", "barAlignment": 0, "drawStyle": "line", "fillOpacity": 0, "gradientMode": "none", "hideFrom": { "legend": false, "tooltip": false, "viz": false }, "lineInterpolation": "linear", "lineWidth": 1, "pointSize": 5, "scaleDistribution": { "type": "linear" }, "showPoints": "auto", "spanNulls": false, "stacking": { "group": "A", "mode": "none" }, "thresholdsStyle": { "mode": "off" } }, "mappings": [], "thresholds": { "mode": "absolute", "steps": [ { "color": "green", "value": null }, { "color": "red", "value": 80 } ] } }, "overrides": [] },
          "gridPos": { "h": 8, "w": 12, "x": 0, "y": 0 },
          "id": 1,
          "options": { "legend": { "calcs": [], "displayMode": "list", "placement": "bottom", "showLegend": true }, "tooltip": { "mode": "single", "sort": "none" } },
          "targets": [ { "datasource": { "type": "prometheus", "uid": "prometheus" }, "editorMode": "code", "expr": "sum(rag_cost_dollars_total)", "legendFormat": "Total Cost", "range": true, "refId": "A" } ],
          "title": "Total RAG Cost ($)",
          "type": "timeseries"
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": { "defaults": { "color": { "mode": "palette-classic" }, "custom": { "axisCenteredZero": false, "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto", "barAlignment": 0, "drawStyle": "line", "fillOpacity": 0, "gradientMode": "none", "hideFrom": { "legend": false, "tooltip": false, "viz": false }, "lineInterpolation": "linear", "lineWidth": 1, "pointSize": 5, "scaleDistribution": { "type": "linear" }, "showPoints": "auto", "spanNulls": false, "stacking": { "group": "A", "mode": "none" }, "thresholdsStyle": { "mode": "off" } }, "mappings": [], "thresholds": { "mode": "absolute", "steps": [ { "color": "green", "value": null }, { "color": "red", "value": 80 } ] } }, "overrides": [] },
          "gridPos": { "h": 8, "w": 12, "x": 12, "y": 0 },
          "id": 2,
          "options": { "legend": { "calcs": [], "displayMode": "list", "placement": "bottom", "showLegend": true }, "tooltip": { "mode": "single", "sort": "none" } },
          "targets": [ { "datasource": { "type": "prometheus", "uid": "prometheus" }, "editorMode": "code", "expr": "rate(rag_token_usage_total[5m])", "legendFormat": "{{type}}", "range": true, "refId": "A" } ],
          "title": "Token Usage Rate (Tokens/sec)",
          "type": "timeseries"
        },
        {
          "datasource": { "type": "prometheus", "uid": "prometheus" },
          "fieldConfig": { "defaults": { "color": { "mode": "palette-classic" }, "custom": { "axisCenteredZero": false, "axisColorMode": "text", "axisLabel": "", "axisPlacement": "auto", "barAlignment": 0, "drawStyle": "line", "fillOpacity": 0, "gradientMode": "none", "hideFrom": { "legend": false, "tooltip": false, "viz": false }, "lineInterpolation": "linear", "lineWidth": 1, "pointSize": 5, "scaleDistribution": { "type": "linear" }, "showPoints": "auto", "spanNulls": false, "stacking": { "group": "A", "mode": "none" }, "thresholdsStyle": { "mode": "off" } }, "mappings": [], "thresholds": { "mode": "absolute", "steps": [ { "color": "green", "value": null }, { "color": "red", "value": 80 } ] } }, "overrides": [] },
          "gridPos": { "h": 8, "w": 24, "x": 0, "y": 8 },
          "id": 3,
          "options": { "legend": { "calcs": [], "displayMode": "list", "placement": "bottom", "showLegend": true }, "tooltip": { "mode": "single", "sort": "none" } },
          "targets": [ { "datasource": { "type": "prometheus", "uid": "prometheus" }, "editorMode": "code", "expr": "histogram_quantile(0.95, sum(rate(rag_request_duration_seconds_bucket{stage=\"total\"}[5m])) by (le))", "legendFormat": "P95 Latency", "range": true, "refId": "A" } ],
          "title": "Request Latency (P95)",
          "type": "timeseries"
        }
      ],
      "refresh": "",
      "schemaVersion": 39,
      "tags": [],
      "templating": { "list": [] },
      "time": { "from": "now-6h", "to": "now" },
      "timepicker": {},
      "timezone": "",
      "title": "RAG API Metrics",
      "uid": "rag-api-metrics",
      "version": 1,
      "weekStart": ""
    }
    ```

2.  **Auto-Provisioning:**
    Terraform reads the file above and creates a ConfigMap.
    Run `terraform apply` to deploy it.

### 3.3 Alerting Rules

Defined in `terraform/modules/monitoring/values.yaml` (passed to Helm).

```yaml
additionalPrometheusRulesMap:
  rule-name:
    groups:
      - name: CostAlerts
        rules:
          - alert: HighCostSpike
            expr: rate(rag_cost_dollars_total[10m]) > 10
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "Spending > $1/min detected"
```

---

## Part 4: Verification

### 4.1 Verification Checklist

- [x] **Terraform Apply**: `terraform apply` succeeds without errors.
- [x] **Pods Running**:
  ```bash
  kubectl get pods -n monitoring
  # Expect: prometheus-server, grafana, alertmanager, operator (All Running)
  ```
- [x] **Grafana Access**:
  ```bash
  kubectl port-forward svc/prometheus-grafana 3200:80 -n monitoring
  ```
  - Open [http://localhost:3200](http://localhost:3200)
  - Login: `admin` / `admin`
- [x] **Metrics Endpoint**: API returns metrics at `/metrics` (After Part 2).
- [x] **Scraping Active**: Prometheus Targets page shows `rag-api` target is UP.
- [x] **Dashboard Data**: Making a request to the API populates the Grafana graphs.

---

**Next Strategic Move:** Proceed to implementation by creating the Terraform module.
```
