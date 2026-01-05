# Phase 5: Monitoring & Observability - Implementation Plan

**Goal:** Instrument the RAG application with comprehensive monitoring, cost tracking, and alerting to ensure production reliability and cost governance. Build dashboards that provide real-time visibility into system health, performance, and economics.

---

## 🏗️ Architectural Context

Phase 5 establishes **Observability Excellence** through:
1.  **Metrics Collection**: Prometheus scraping application and infrastructure metrics.
2.  **Visualization**: Grafana dashboards for cost, performance, and health monitoring.
3.  **Alerting**: Proactive notifications for anomalies, errors, and budget thresholds.
4.  **Tracing**: Distributed tracing to debug complex request flows.

**Engineering Outcomes:**
- Real-time cost visibility (cost per query, daily spend trends).
- Performance monitoring (latency, error rates, throughput).
- Proactive alerting before issues impact users.
- Full request tracing from API to LLM to vector DB.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Prometheus & Grafana Deployment](#part-1-prometheus--grafana-deployment)**
- [1.1 Deploy Prometheus](#11-deploy-prometheus)
- [1.2 Deploy Grafana](#12-deploy-grafana)
- [1.3 Configure Scraping](#13-configure-scraping)

**[Part 2: Application Instrumentation](#part-2-application-instrumentation)**
- [2.1 Metrics Library Setup](#21-metrics-library-setup)
- [2.2 Request Latency Tracking](#22-request-latency-tracking)
- [2.3 LLM Token Usage Tracking](#23-llm-token-usage-tracking)
- [2.4 Cost Calculation](#24-cost-calculation)
- [2.5 Error Rate Metrics](#25-error-rate-metrics)

**[Part 3: Cost Tracking Dashboard](#part-3-cost-tracking-dashboard)**
- [3.1 Grafana Dashboard JSON](#31-grafana-dashboard-json)
- [3.2 Cost Queries](#32-cost-queries)

**[Part 4: CloudWatch Integration](#part-4-cloudwatch-integration)**
- [4.1 Log Aggregation](#41-log-aggregation)
- [4.2 Custom Metrics](#42-custom-metrics)

**[Part 5: Alerting](#part-5-alerting)**
- [5.1 Prometheus Alert Rules](#51-prometheus-alert-rules)
- [5.2 SNS Notification Setup](#52-sns-notification-setup)

**[Part 6: Distributed Tracing](#part-6-distributed-tracing)**
- [6.1 AWS X-Ray Setup](#61-aws-x-ray-setup)
- [6.2 Trace Instrumentation](#62-trace-instrumentation)

**[Part 7: Verification](#part-7-verification)**

---

## Prerequisites

- **Phase 4 Complete**: CI/CD pipelines operational.
- **Kubernetes Cluster**: Running with sufficient resources for monitoring stack.
- **AWS Account**: For CloudWatch and X-Ray.

---

## Part 1: Prometheus & Grafana Deployment

### 1.1 Deploy Prometheus
**File:** `kubernetes/monitoring/prometheus-deployment.yaml`

Deploy Prometheus with persistent storage.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
      - job_name: 'rag-api'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - dev
                - staging
                - prod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: rag-api
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
      
      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
          - role: node
        relabel_configs:
          - action: labelmap
            regex: __meta_kubernetes_node_label_(.+)
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: prom/prometheus:v2.48.0
        args:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus'
          - '--storage.tsdb.retention.time=30d'
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: storage
          mountPath: /prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: storage
        persistentVolumeClaim:
          claimName: prometheus-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus
  namespace: monitoring
spec:
  selector:
    app: prometheus
  ports:
    - port: 9090
      targetPort: 9090
  type: ClusterIP
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: prometheus-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
```

### 1.2 Deploy Grafana
**File:** `kubernetes/monitoring/grafana-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.2.0
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: grafana-secrets
              key: admin-password
        - name: GF_INSTALL_PLUGINS
          value: "grafana-piechart-panel,grafana-clock-panel"
        volumeMounts:
        - name: storage
          mountPath: /var/lib/grafana
        - name: datasources
          mountPath: /etc/grafana/provisioning/datasources
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: grafana-pvc
      - name: datasources
        configMap:
          name: grafana-datasources
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: monitoring
data:
  prometheus.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus:9090
        isDefault: true
---
apiVersion: v1
kind: Service
metadata:
  name: grafana
  namespace: monitoring
spec:
  selector:
    app: grafana
  ports:
    - port: 3000
      targetPort: 3000
  type: LoadBalancer
```

### 1.3 Configure Scraping
**File:** `kubernetes/monitoring/rbac.yaml`

Service account for Prometheus to discover pods.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups: [""]
  resources:
  - nodes
  - nodes/proxy
  - services
  - endpoints
  - pods
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions"]
  resources:
  - ingresses
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
```

---

## Part 2: Application Instrumentation

### 2.1 Metrics Library Setup
**File:** `api/metrics.py`

Centralized metrics definitions using Prometheus client.

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import time

# Request metrics
request_count = Counter(
    'rag_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

request_latency = Histogram(
    'rag_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

# LLM metrics
llm_token_usage = Counter(
    'rag_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']  # type: input/output
)

llm_requests = Counter(
    'rag_llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

llm_latency = Histogram(
    'rag_llm_duration_seconds',
    'LLM request latency',
    ['model']
)

# Cost metrics
cost_total = Counter(
    'rag_cost_dollars_total',
    'Total cost in dollars',
    ['service']  # service: llm, embeddings, storage
)

cost_per_query = Histogram(
    'rag_cost_per_query_dollars',
    'Cost per query in dollars',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Error metrics
error_count = Counter(
    'rag_errors_total',
    'Total number of errors',
    ['type', 'endpoint']
)

# Vector DB metrics
vector_search_latency = Histogram(
    'rag_vector_search_duration_seconds',
    'Vector search latency'
)

# Active requests
active_requests = Gauge(
    'rag_active_requests',
    'Number of active requests'
)

def metrics_endpoint():
    """Expose metrics for Prometheus scraping"""
    return Response(content=generate_latest(), media_type="text/plain")
```

### 2.2 Request Latency Tracking
**File:** `api/middleware/metrics_middleware.py`

Middleware to automatically track request metrics.

```python
from fastapi import Request
from api.metrics import (
    request_count, 
    request_latency, 
    active_requests,
    error_count
)
import time

async def metrics_middleware(request: Request, call_next):
    # Track active requests
    active_requests.inc()
    
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    try:
        response = await call_next(request)
        status = response.status_code
        
        # Record metrics
        request_count.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        duration = time.time() - start_time
        request_latency.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        return response
    
    except Exception as e:
        error_count.labels(
            type=type(e).__name__,
            endpoint=endpoint
        ).inc()
        raise
    
    finally:
        active_requests.dec()
```

### 2.3 LLM Token Usage Tracking
**File:** `api/services/llm_service.py` (enhanced)

Track token usage and costs in LLM service.

```python
from api.services.bedrock_service import bedrock_client
from api.config import settings
from api.metrics import llm_token_usage, llm_requests, llm_latency, cost_total
import time

# Pricing per 1K tokens (as of 2026)
PRICING = {
    "amazon.nova-2-lite-v1:0": {
        "input": 0.0006,
        "output": 0.0024
    },
    "amazon.nova-2-pro-v1:0": {
        "input": 0.0008,
        "output": 0.0032
    }
}

class LLMService:
    def __init__(self, model_id="amazon.nova-2-lite-v1:0"):
        self.model_id = model_id
        self.use_guardrails = hasattr(settings, 'guardrail_id')

    def generate_response(self, prompt: str, system_prompt: str = "") -> dict:
        start_time = time.time()
        
        body = {
            "inferenceConfig": {"max_new_tokens": 1000},
            "messages": [
                {"role": "system", "content": [{"text": system_prompt}]},
                {"role": "user", "content": [{"text": prompt}]}
            ]
        }
        
        if self.use_guardrails:
            body["guardrailIdentifier"] = settings.guardrail_id
            body["guardrailVersion"] = "DRAFT"

        try:
            response = bedrock_client.invoke(self.model_id, body)
            
            # Extract token usage
            usage = response.get('usage', {})
            input_tokens = usage.get('inputTokens', 0)
            output_tokens = usage.get('outputTokens', 0)
            
            # Record token metrics
            llm_token_usage.labels(
                model=self.model_id,
                type='input'
            ).inc(input_tokens)
            
            llm_token_usage.labels(
                model=self.model_id,
                type='output'
            ).inc(output_tokens)
            
            # Calculate cost
            pricing = PRICING.get(self.model_id, PRICING["amazon.nova-2-lite-v1:0"])
            cost = (
                (input_tokens / 1000) * pricing['input'] +
                (output_tokens / 1000) * pricing['output']
            )
            
            cost_total.labels(service='llm').inc(cost)
            
            # Record latency
            duration = time.time() - start_time
            llm_latency.labels(model=self.model_id).observe(duration)
            
            # Record success
            llm_requests.labels(
                model=self.model_id,
                status='success'
            ).inc()
            
            return {
                'text': response['output']['message']['content'][0]['text'],
                'tokens': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': input_tokens + output_tokens
                },
                'cost': cost
            }
        
        except Exception as e:
            llm_requests.labels(
                model=self.model_id,
                status='error'
            ).inc()
            raise

llm_service = LLMService()
```

### 2.4 Cost Calculation
**File:** `api/services/rag_service.py` (enhanced)

Track end-to-end query costs.

```python
from api.services.vector_store import vector_store
from api.services.llm_service import llm_service
from api.prompts.templates import get_prompt
from api.metrics import cost_per_query, cost_total
import time

class RAGService:
    def query(self, question: str, domain: str = None, use_hybrid=True):
        start_time = time.time()
        query_cost = 0.0
        
        # 1. Retrieve (minimal cost for vector search)
        filters = {"domain": domain} if domain else None
        
        if use_hybrid:
            results = vector_store.hybrid_search(
                question, top_k=3, filter=filters, alpha=0.7
            )
        else:
            results = vector_store.search(question, top_k=3, filter=filters)
        
        # Estimate embedding cost (Titan V2: ~$0.0001 per 1K tokens)
        embedding_cost = 0.0001 * (len(question.split()) / 1000)
        cost_total.labels(service='embeddings').inc(embedding_cost)
        query_cost += embedding_cost
        
        context_chunks = results['documents']
        context_text = "\\n\\n".join(context_chunks)
        
        # 2. Get domain-specific prompts
        system_prompt, user_prompt = get_prompt(
            domain or "general",
            context_text,
            question
        )
        
        # 3. Generate with cost tracking
        llm_response = llm_service.generate_response(user_prompt, system_prompt)
        query_cost += llm_response['cost']
        
        # Record total query cost
        cost_per_query.observe(query_cost)
        
        execution_time = time.time() - start_time
        
        return {
            "question": question,
            "answer": llm_response['text'],
            "sources": results['metadatas'],
            "domain": domain,
            "execution_time_ms": round(execution_time * 1000, 2),
            "cost": query_cost,
            "tokens": llm_response['tokens']
        }

rag_service = RAGService()
```

### 2.5 Error Rate Metrics
Covered in metrics_middleware.py above.

---

## Part 3: Cost Tracking Dashboard

### 3.1 Grafana Dashboard JSON
**File:** `kubernetes/monitoring/dashboards/cost-tracking.json`

Complete Grafana dashboard for cost monitoring.

```json
{
  "dashboard": {
    "title": "RAG Cost Tracking",
    "panels": [
      {
        "id": 1,
        "title": "Cost Per Query (Last 24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "avg(rag_cost_per_query_dollars) * 1000",
            "legendFormat": "Avg Cost (cents)"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currencyUSD",
            "decimals": 4
          }
        }
      },
      {
        "id": 2,
        "title": "Total Cost by Service",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (service) (rag_cost_dollars_total)",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "Daily Cost Trend",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(increase(rag_cost_dollars_total[1d]))",
            "legendFormat": "Daily Cost"
          }
        ]
      },
      {
        "id": 4,
        "title": "LLM Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "sum by (type) (rate(rag_llm_tokens_total[5m]))",
            "legendFormat": "{{type}}"
          }
        ]
      },
      {
        "id": 5,
        "title": "Cost by Model",
        "type": "table",
        "targets": [
          {
            "expr": "sum by (model) (rag_cost_dollars_total)",
            "format": "table"
          }
        ]
      }
    ]
  }
}
```

### 3.2 Cost Queries
**Common Prometheus queries for cost analysis:**

```promql
# Average cost per query (last hour)
avg_over_time(rag_cost_per_query_dollars[1h])

# Total daily cost
sum(increase(rag_cost_dollars_total[1d]))

# Cost breakdown by service
sum by (service) (rag_cost_dollars_total)

# Queries per dollar (efficiency metric)
sum(rate(rag_requests_total[5m])) / sum(rate(rag_cost_dollars_total[5m]))

# Token usage rate
sum(rate(rag_llm_tokens_total[5m]))
```

---

## Part 4: CloudWatch Integration

### 4.1 Log Aggregation
**File:** `kubernetes/monitoring/fluentbit-config.yaml`

Forward logs to CloudWatch.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: monitoring
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
    
    [INPUT]
        Name              tail
        Path              /var/log/containers/rag-api*.log
        Parser            docker
        Tag               kube.*
    
    [OUTPUT]
        Name              cloudwatch_logs
        Match             kube.*
        region            ap-southeast-2
        log_group_name    /aws/eks/llmops-rag
        log_stream_prefix rag-api-
        auto_create_group true
```

### 4.2 Custom Metrics
**File:** `api/cloudwatch.py`

Send custom metrics to CloudWatch.

```python
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch', region_name='ap-southeast-2')

def put_cost_metric(cost: float, domain: str):
    """Send cost metric to CloudWatch"""
    cloudwatch.put_metric_data(
        Namespace='RAG/Application',
        MetricData=[
            {
                'MetricName': 'QueryCost',
                'Dimensions': [
                    {'Name': 'Domain', 'Value': domain}
                ],
                'Value': cost,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            }
        ]
    )
```

---

## Part 5: Alerting

### 5.1 Prometheus Alert Rules
**File:** `kubernetes/monitoring/alert-rules.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-alerts
  namespace: monitoring
data:
  alerts.yml: |
    groups:
      - name: cost_alerts
        interval: 5m
        rules:
          - alert: HighQueryCost
            expr: avg_over_time(rag_cost_per_query_dollars[5m]) > 0.05
            for: 10m
            labels:
              severity: warning
            annotations:
              summary: "High cost per query detected"
              description: "Average query cost is {{ $value | humanize }} (threshold: $0.05)"
          
          - alert: DailyCostBudgetExceeded
            expr: sum(increase(rag_cost_dollars_total[1d])) > 10
            labels:
              severity: critical
            annotations:
              summary: "Daily cost budget exceeded"
              description: "Daily cost is ${{ $value | humanize }} (budget: $10)"
      
      - name: performance_alerts
        interval: 1m
        rules:
          - alert: HighErrorRate
            expr: rate(rag_errors_total[5m]) > 0.05
            for: 5m
            labels:
              severity: critical
            annotations:
              summary: "High error rate detected"
              description: "Error rate is {{ $value | humanizePercentage }}"
          
          - alert: HighLatency
            expr: histogram_quantile(0.95, rate(rag_request_duration_seconds_bucket[5m])) > 2
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High request latency"
              description: "P95 latency is {{ $value }}s (threshold: 2s)"
```

### 5.2 SNS Notification Setup
**File:** `terraform/modules/monitoring/sns.tf`

```hcl
resource "aws_sns_topic" "alerts" {
  name = "rag-monitoring-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Alarm for cost anomaly
resource "aws_cloudwatch_metric_alarm" "cost_anomaly" {
  alarm_name          = "rag-cost-anomaly"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "QueryCost"
  namespace           = "RAG/Application"
  period              = "300"
  statistic           = "Average"
  threshold           = "0.05"
  alarm_description   = "Alert when query cost exceeds threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## Part 6: Distributed Tracing

### 6.1 AWS X-Ray Setup
**File:** `api/xray.py`

```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

# Configure X-Ray
xray_recorder.configure(
    service='rag-api',
    sampling=True,
    context_missing='LOG_ERROR'
)

def init_xray(app):
    """Initialize X-Ray for FastAPI"""
    XRayMiddleware(app, xray_recorder)
```

### 6.2 Trace Instrumentation
**File:** `api/services/rag_service.py` (with tracing)

```python
from aws_xray_sdk.core import xray_recorder

class RAGService:
    @xray_recorder.capture('rag_query')
    def query(self, question: str, domain: str = None, use_hybrid=True):
        # Add metadata to trace
        xray_recorder.put_metadata('domain', domain)
        xray_recorder.put_metadata('question_length', len(question))
        
        with xray_recorder.capture('vector_search'):
            results = vector_store.hybrid_search(question, top_k=3)
        
        with xray_recorder.capture('llm_generation'):
            llm_response = llm_service.generate_response(user_prompt, system_prompt)
        
        return result
```

---


## Part 6.5: Integration & Deployment

> **Critical**: This section shows how to deploy and configure Prometheus, Grafana, and application instrumentation for observability.

### 6.5.1 Deploy Prometheus to Minikube

**1. Create monitoring namespace:**
```bash
kubectl create namespace monitoring
```

**2. Apply Prometheus manifests:**
```bash
kubectl apply -f kubernetes/monitoring/prometheus-config.yaml -n monitoring
kubectl apply -f kubernetes/monitoring/prometheus-deployment.yaml -n monitoring
```

**3. Verify Prometheus is running:**
```bash
kubectl get pods -n monitoring
# Should see: prometheus-xxxxx   1/1   Running

kubectl logs -l app=prometheus -n monitoring --tail=20
# Should see: "Server is ready to receive web requests"
```

**4. Port forward to access Prometheus UI:**
```bash
kubectl port-forward service/prometheus-service 9090:9090 -n monitoring &
```

**5. Verify Prometheus is scraping:**
```bash
curl http://localhost:9090/api/v1/targets
# Should show targets with state="up"
```

### 6.5.2 Deploy Grafana

**1. Apply Grafana manifests:**
```bash
kubectl apply -f kubernetes/monitoring/grafana-deployment.yaml -n monitoring
```

**2. Verify Grafana is running:**
```bash
kubectl get pods -n monitoring | grep grafana
# Should see: grafana-xxxxx   1/1   Running
```

**3. Get Grafana admin password:**
```bash
kubectl get secret grafana-admin -n monitoring -o jsonpath="{.data.password}" | base64 --decode
# Save this password
```

**4. Port forward to access Grafana UI:**
```bash
kubectl port-forward service/grafana-service 3000:3000 -n monitoring &
```

**5. Login to Grafana:**
```
http://localhost:3000
Username: admin
Password: (from step 3)
```

### 6.5.3 Configure Grafana Data Source

**1. Add Prometheus as data source:**
- Navigate to Configuration → Data Sources
- Click "Add data source"
- Select "Prometheus"
- URL: `http://prometheus-service.monitoring.svc.cluster.local:9090`
- Click "Save & Test"

**2. Or apply via ConfigMap:**
```bash
kubectl apply -f kubernetes/monitoring/grafana-datasource.yaml -n monitoring
kubectl rollout restart deployment/grafana -n monitoring
```

### 6.5.4 Import Grafana Dashboards

**1. Import RAG metrics dashboard:**
- Navigate to Dashboards → Import
- Upload `kubernetes/monitoring/dashboards/rag-metrics.json`
- Select Prometheus data source
- Click "Import"

**2. Or apply via ConfigMap:**
```bash
kubectl create configmap grafana-dashboards \
  --from-file=kubernetes/monitoring/dashboards/ \
  -n monitoring
kubectl label configmap grafana-dashboards grafana_dashboard=1 -n monitoring
```

### 6.5.5 Update Application with Metrics

**1. Add Prometheus client to requirements.txt:**
```bash
echo "prometheus-client==0.19.0" >> api/requirements.txt
```

**2. Update main.py with metrics endpoint:**
```python
from prometheus_client import make_asgi_app, Counter, Histogram
import time

# Metrics
query_counter = Counter('rag_queries_total', 'Total RAG queries')
query_duration = Histogram('rag_query_duration_seconds', 'Query duration')

# Add metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

**3. Rebuild and redeploy:**
```bash
eval $(minikube docker-env)
docker build -t llmops-rag-api:latest -f api/Dockerfile .
kubectl delete pod -l app=rag-api -n dev
kubectl wait --for=condition=ready pod -l app=rag-api -n dev --timeout=120s
```

### 6.5.6 Configure ServiceMonitor for Prometheus

**1. Apply ServiceMonitor:**
```bash
kubectl apply -f kubernetes/monitoring/servicemonitor.yaml -n dev
```

**2. Verify Prometheus is scraping the API:**
```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="rag-api")'
# Should show state="up"
```

### 6.5.7 Configure CloudWatch Integration (Optional)

**1. Create IAM role for CloudWatch:**
```bash
aws iam create-role --role-name EKS-CloudWatch-Role \
  --assume-role-policy-document file://iam/cloudwatch-trust-policy.json
```

**2. Attach CloudWatch policy:**
```bash
aws iam attach-role-policy \
  --role-name EKS-CloudWatch-Role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
```

**3. Deploy CloudWatch agent:**
```bash
kubectl apply -f kubernetes/monitoring/cloudwatch-agent.yaml -n monitoring
```

### 6.5.8 Test Metrics Collection

**1. Generate test traffic:**
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"question": "test query '$i'", "domain": "general"}'
  sleep 1
done
```

**2. Verify metrics in Prometheus:**
```bash
curl http://localhost:9090/api/v1/query?query=rag_queries_total
# Should show count increasing
```

**3. Check Grafana dashboard:**
- Open http://localhost:3000
- Navigate to RAG Metrics dashboard
- Should see query count and latency graphs

### 6.5.9 Troubleshooting Common Issues

**Issue: Prometheus not scraping targets**
```bash
# Check ServiceMonitor exists
kubectl get servicemonitor -n dev

# Verify Prometheus config includes the job
kubectl exec -it deployment/prometheus -n monitoring -- cat /etc/prometheus/prometheus.yml | grep rag-api
```

**Issue: Grafana can't connect to Prometheus**
```bash
# Test DNS resolution
kubectl exec -it deployment/grafana -n monitoring -- nslookup prometheus-service.monitoring.svc.cluster.local

# Check if Prometheus service is accessible
kubectl exec -it deployment/grafana -n monitoring -- curl http://prometheus-service.monitoring.svc.cluster.local:9090/api/v1/status/config
```

**Issue: Metrics endpoint returns 404**
```bash
# Verify metrics endpoint exists
kubectl exec -it deployment/rag-api -n dev -- curl http://localhost:8000/metrics

# Check if prometheus-client is installed
kubectl exec -it deployment/rag-api -n dev -- pip list | grep prometheus
```

**Issue: CloudWatch agent fails to start**
```bash
# Check IAM role is attached
kubectl describe pod -l app=cloudwatch-agent -n monitoring | grep "AWS_ROLE_ARN"

# Verify credentials
kubectl exec -it deployment/cloudwatch-agent -n monitoring -- aws sts get-caller-identity
```

---

## Part 7: Verification

### 7.1 Verification Steps

**1. Verify Prometheus Scraping**
```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Check targets
curl http://localhost:9090/api/v1/targets

# Query metrics
curl 'http://localhost:9090/api/v1/query?query=rag_requests_total'
```

**2. Verify Grafana Dashboards**
```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access: http://localhost:3000
# Login: admin / <password from secret>
# Verify dashboards load and show data
```

**3. Test Cost Tracking**
```bash
# Make test queries
for i in {1..10}; do
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"question": "test query '$i'", "domain": "general"}'
done

# Check cost metrics in Grafana
# Verify cost per query is calculated
```

**4. Test Alerting**
```bash
# Trigger high cost alert (make expensive queries)
# Check Prometheus alerts page
curl http://localhost:9090/alerts

# Verify SNS email received
```

### 7.2 Verification Checklist

### ✅ Prometheus & Grafana
- [ ] Prometheus deployed and scraping metrics
- [ ] Grafana accessible with admin login
- [ ] Datasource configured correctly
- [ ] Metrics visible in Prometheus UI

### ✅ Application Metrics
- [ ] Request count incrementing
- [ ] Latency histograms populating
- [ ] Token usage tracked per request
- [ ] Cost calculated accurately
- [ ] Error metrics captured

### ✅ Cost Dashboard
- [ ] Cost per query displayed
- [ ] Daily cost trend visible
- [ ] Service breakdown chart working
- [ ] Token usage graph showing data
- [ ] Model comparison table accurate

### ✅ Alerting
- [ ] Alert rules loaded in Prometheus
- [ ] SNS topic created
- [ ] Email subscription confirmed
- [ ] Test alert fires correctly
- [ ] Notification received

### ✅ Tracing
- [ ] X-Ray daemon running
- [ ] Traces visible in AWS Console
- [ ] Service map shows components
- [ ] Latency breakdown available

---

**Next Strategic Move:** With comprehensive monitoring in place, we proceed to **Phase 6: MLOps/LLMOps Features** to add semantic caching, intelligent routing, and experiment tracking for continuous improvement.
