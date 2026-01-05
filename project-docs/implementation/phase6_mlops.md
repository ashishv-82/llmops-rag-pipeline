# Phase 6: MLOps/LLMOps Features - Implementation Plan

**Goal:** Implement advanced ML operations capabilities including semantic caching for cost reduction, intelligent model routing for optimization, prompt versioning for experimentation, and automated evaluation pipelines for quality assurance.

---

## 🏗️ Architectural Context

Phase 6 adds **ML Operations Maturity** through:
1.  **Cost Optimization**: Semantic caching reducing LLM calls by 60-80%.
2.  **Intelligent Routing**: Automatic model selection based on query complexity and domain.
3.  **Experimentation**: A/B testing framework for prompts and models.
4.  **Quality Assurance**: Automated evaluation pipelines with quality metrics.
5.  **Drift Detection**: Monitoring query patterns for distribution shifts.

**Engineering Outcomes:**
- 60%+ cost reduction through caching and routing.
- Data-driven model selection with measurable quality/cost trade-offs.
- Continuous improvement through experimentation and evaluation.
- Early detection of model degradation or data drift.

---

## Table of Contents

**[Prerequisites](#prerequisites)**

**[Part 1: Semantic Caching (Redis)](#part-1-semantic-caching-redis)**
- [1.1 Deploy Redis](#11-deploy-redis)
- [1.2 Embedding Cache](#12-embedding-cache)
- [1.3 Response Cache](#13-response-cache)
- [1.4 Cache Metrics](#14-cache-metrics)

**[Part 2: Intelligent LLM Routing](#part-2-intelligent-llm-routing)**
- [2.1 Query Complexity Analysis](#21-query-complexity-analysis)
- [2.2 Routing Logic](#22-routing-logic)
- [2.3 Cost Tracking](#23-cost-tracking)

**[Part 3: Prompt Versioning](#part-3-prompt-versioning)**
- [3.1 Version Control System](#31-version-control-system)
- [3.2 A/B Testing](#32-ab-testing)

**[Part 4: MLflow Setup](#part-4-mlflow-setup)**
- [4.1 Deploy MLflow](#41-deploy-mlflow)
- [4.2 Experiment Tracking](#42-experiment-tracking)
- [4.3 Model Registry](#43-model-registry)

**[Part 5: Evaluation Pipeline](#part-5-evaluation-pipeline)**
- [5.1 Quality Metrics](#51-quality-metrics)
- [5.2 Automated Testing](#52-automated-testing)
- [5.3 Evaluation Reports](#53-evaluation-reports)

**[Part 6: Data Drift Detection](#part-6-data-drift-detection)**
- [6.1 Query Pattern Monitoring](#61-query-pattern-monitoring)
- [6.2 Drift Alerts](#62-drift-alerts)

**[Part 7: Verification](#part-7-verification)**

---

## Prerequisites

- **Phase 5 Complete**: Monitoring and metrics infrastructure operational.
- **Kubernetes Cluster**: With resources for Redis and MLflow.
- **Python Libraries**: `redis`, `mlflow`, `scikit-learn`, `nltk`.

---

## Part 1: Semantic Caching (Redis)

### 1.1 Deploy Redis
**File:** `kubernetes/base/redis-deployment.yaml`

Deploy Redis for caching embeddings and LLM responses.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7.2-alpine
        ports:
        - containerPort: 6379
        command:
          - redis-server
          - --maxmemory
          - 2gb
          - --maxmemory-policy
          - allkeys-lru
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: dev
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: dev
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

### 1.2 Embedding Cache
**File:** `api/services/cache_service.py`

Implement semantic caching with similarity-based lookup.

```python
import redis
import hashlib
import json
import numpy as np
from typing import Optional, Tuple
from api.services.embedding_service import embedding_service
from api.metrics import cache_hit_rate

class CacheService:
    def __init__(self, host='redis-service', port=6379):
        self.redis = redis.Redis(
            host=host,
            port=port,
            decode_responses=True
        )
        self.embedding_ttl = 86400  # 24 hours
        self.response_ttl = 3600    # 1 hour
        self.similarity_threshold = 0.95
    
    def _generate_key(self, text: str, prefix: str) -> str:
        """Generate cache key from text"""
        hash_obj = hashlib.sha256(text.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def get_embedding(self, text: str) -> Optional[list]:
        """Get cached embedding"""
        key = self._generate_key(text, "embedding")
        cached = self.redis.get(key)
        
        if cached:
            cache_hit_rate.labels(type='embedding', hit='true').inc()
            return json.loads(cached)
        
        cache_hit_rate.labels(type='embedding', hit='false').inc()
        return None
    
    def set_embedding(self, text: str, embedding: list):
        """Cache embedding"""
        key = self._generate_key(text, "embedding")
        self.redis.setex(
            key,
            self.embedding_ttl,
            json.dumps(embedding)
        )
    
    def find_similar_response(
        self, 
        query: str, 
        query_embedding: list,
        domain: str
    ) -> Optional[Tuple[str, float]]:
        """
        Find cached response for similar query using semantic similarity.
        Returns (response, similarity_score) if found, else None.
        """
        # Search pattern for domain-specific responses
        pattern = f"response:{domain}:*"
        keys = self.redis.keys(pattern)
        
        if not keys:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        for key in keys[:100]:  # Limit search to recent 100
            cached_data = self.redis.get(key)
            if not cached_data:
                continue
            
            data = json.loads(cached_data)
            cached_embedding = data.get('query_embedding')
            
            if not cached_embedding:
                continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(
                query_embedding,
                cached_embedding
            )
            
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = data.get('response')
        
        if best_match:
            cache_hit_rate.labels(type='response', hit='true').inc()
            return best_match, best_similarity
        
        cache_hit_rate.labels(type='response', hit='false').inc()
        return None
    
    def set_response(
        self,
        query: str,
        query_embedding: list,
        response: str,
        domain: str
    ):
        """Cache query-response pair with embedding"""
        key = self._generate_key(f"{domain}:{query}", "response")
        
        data = {
            'query': query,
            'query_embedding': query_embedding,
            'response': response,
            'domain': domain
        }
        
        self.redis.setex(
            f"response:{domain}:{key}",
            self.response_ttl,
            json.dumps(data)
        )
    
    def _cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def invalidate_domain(self, domain: str):
        """Invalidate all cached responses for a domain"""
        pattern = f"response:{domain}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

cache_service = CacheService()
```

### 1.3 Response Cache
Covered in the `find_similar_response` and `set_response` methods above.

### 1.4 Cache Metrics
**File:** `api/metrics.py` (add to existing)

```python
from prometheus_client import Counter

cache_hit_rate = Counter(
    'rag_cache_hits_total',
    'Cache hit/miss count',
    ['type', 'hit']  # type: embedding/response, hit: true/false
)

cache_savings = Counter(
    'rag_cache_savings_dollars',
    'Cost savings from cache hits'
)
```

---

## Part 2: Intelligent LLM Routing

### 2.1 Query Complexity Analysis
**File:** `api/services/routing_service.py`

Analyze query complexity to route to appropriate model.

```python
import re
from typing import Literal
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

ModelTier = Literal['lite', 'pro']

class RoutingService:
    def __init__(self):
        # Complexity thresholds
        self.word_count_threshold = 50
        self.sentence_count_threshold = 3
        
        # Domain-specific routing
        self.domain_routing = {
            'legal': {
                'default': 'pro',  # Legal queries need high accuracy
                'simple_threshold': 20  # Very short legal queries can use lite
            },
            'hr': {
                'default': 'lite',  # HR queries are typically simpler
                'complex_threshold': 100  # Long HR queries need pro
            },
            'engineering': {
                'default': 'lite',
                'complex_threshold': 75
            },
            'general': {
                'default': 'lite',
                'complex_threshold': 50
            }
        }
    
    def analyze_complexity(self, query: str, domain: str = 'general') -> ModelTier:
        """
        Determine which model to use based on query complexity and domain.
        Returns 'lite' or 'pro'.
        """
        # Get domain config
        config = self.domain_routing.get(domain, self.domain_routing['general'])
        
        # Word count
        words = word_tokenize(query.lower())
        word_count = len(words)
        
        # Sentence count
        sentences = sent_tokenize(query)
        sentence_count = len(sentences)
        
        # Check for complex patterns
        has_technical_terms = self._has_technical_terms(query)
        has_multiple_questions = query.count('?') > 1
        has_conditional = bool(re.search(r'\b(if|when|unless|provided|assuming)\b', query.lower()))
        
        # Domain-specific logic
        if domain == 'legal':
            # Legal: default to pro unless very simple
            if word_count < config['simple_threshold'] and not has_conditional:
                return 'lite'
            return 'pro'
        
        elif domain == 'hr':
            # HR: default to lite unless complex
            if word_count > config['complex_threshold'] or has_multiple_questions:
                return 'pro'
            return 'lite'
        
        else:
            # General/Engineering: complexity-based
            complexity_score = (
                (word_count > config['complex_threshold']) * 2 +
                (sentence_count > self.sentence_count_threshold) * 1 +
                has_technical_terms * 1 +
                has_multiple_questions * 1 +
                has_conditional * 1
            )
            
            # If complexity score >= 3, use pro
            return 'pro' if complexity_score >= 3 else 'lite'
    
    def _has_technical_terms(self, query: str) -> bool:
        """Check for technical terminology"""
        technical_indicators = [
            'algorithm', 'implementation', 'architecture', 'deployment',
            'configuration', 'infrastructure', 'optimization', 'integration',
            'compliance', 'regulation', 'statute', 'provision'
        ]
        query_lower = query.lower()
        return any(term in query_lower for term in technical_indicators)

routing_service = RoutingService()
```

### 2.2 Routing Logic
**File:** `api/services/rag_service.py` (enhanced)

Integrate routing into RAG service.

```python
from api.services.routing_service import routing_service
from api.services.cache_service import cache_service
from api.metrics import cost_total, cache_savings

class RAGService:
    def query(self, question: str, domain: str = None, use_hybrid=True):
        start_time = time.time()
        query_cost = 0.0
        
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(question)
        
        # Check cache first
        cached_response = cache_service.find_similar_response(
            question,
            query_embedding,
            domain or 'general'
        )
        
        if cached_response:
            response_text, similarity = cached_response
            
            # Estimate saved cost (avg query cost ~$0.01)
            saved_cost = 0.01
            cache_savings.inc(saved_cost)
            
            return {
                "question": question,
                "answer": response_text,
                "cached": True,
                "cache_similarity": similarity,
                "cost": 0.0,
                "cost_saved": saved_cost
            }
        
        # Determine model tier
        model_tier = routing_service.analyze_complexity(question, domain or 'general')
        model_id = f"amazon.nova-2-{model_tier}-v1:0"
        
        # Retrieve with hybrid search
        filters = {"domain": domain} if domain else None
        results = vector_store.hybrid_search(
            question, top_k=3, filter=filters, alpha=0.7
        )
        
        context_chunks = results['documents']
        context_text = "\\n\\n".join(context_chunks)
        
        # Get domain-specific prompts
        system_prompt, user_prompt = get_prompt(
            domain or "general",
            context_text,
            question
        )
        
        # Generate with selected model
        llm_service_instance = LLMService(model_id=model_id)
        llm_response = llm_service_instance.generate_response(user_prompt, system_prompt)
        
        query_cost += llm_response['cost']
        
        # Cache the response
        cache_service.set_response(
            question,
            query_embedding,
            llm_response['text'],
            domain or 'general'
        )
        
        execution_time = time.time() - start_time
        
        return {
            "question": question,
            "answer": llm_response['text'],
            "sources": results['metadatas'],
            "domain": domain,
            "model_used": model_tier,
            "cached": False,
            "execution_time_ms": round(execution_time * 1000, 2),
            "cost": query_cost,
            "tokens": llm_response['tokens']
        }

rag_service = RAGService()
```

### 2.3 Cost Tracking
**File:** `api/metrics.py` (add to existing)

```python
routing_decisions = Counter(
    'rag_routing_decisions_total',
    'Model routing decisions',
    ['domain', 'model_tier']
)

routing_savings = Counter(
    'rag_routing_savings_dollars',
    'Cost savings from intelligent routing'
)
```

---

## Part 3: Prompt Versioning

### 3.1 Version Control System
**File:** `api/prompts/versions.py`

Manage prompt versions with A/B testing support.

```python
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
import random

@dataclass
class PromptVersion:
    version_id: str
    name: str
    system_prompt: str
    user_template: str
    created_at: datetime
    active: bool = True
    weight: float = 1.0  # For A/B testing

class PromptVersionManager:
    def __init__(self):
        self.versions: Dict[str, Dict[str, PromptVersion]] = {}
        self._load_versions()
    
    def _load_versions(self):
        """Load prompt versions from configuration"""
        # Legal domain versions
        self.versions['legal'] = {
            'v1': PromptVersion(
                version_id='legal_v1',
                name='Standard Legal',
                system_prompt="""You are a legal document assistant. Provide precise, citation-based answers.
Always reference specific sections or clauses. Use formal legal terminology.""",
                user_template="""Based on the following legal documents:

{context}

Question: {question}

Provide a detailed answer with specific citations.""",
                created_at=datetime(2026, 1, 1),
                weight=0.5
            ),
            'v2': PromptVersion(
                version_id='legal_v2',
                name='Concise Legal',
                system_prompt="""You are a legal document assistant. Provide concise, accurate answers with citations.
Focus on the most relevant information.""",
                user_template="""Legal Documents:

{context}

Question: {question}

Provide a concise answer with key citations only.""",
                created_at=datetime(2026, 1, 5),
                weight=0.5
            )
        }
        
        # Add more domain versions...
    
    def get_prompt(
        self,
        domain: str,
        context: str,
        question: str,
        version_id: str = None
    ) -> tuple[str, str, str]:
        """
        Get prompt for domain. If version_id not specified, use A/B testing.
        Returns (system_prompt, user_prompt, version_id)
        """
        domain_versions = self.versions.get(domain, self.versions.get('general', {}))
        
        if not domain_versions:
            raise ValueError(f"No prompts found for domain: {domain}")
        
        # Get specific version or select via weighted random
        if version_id:
            version = domain_versions.get(version_id)
        else:
            version = self._weighted_random_selection(domain_versions)
        
        system_prompt = version.system_prompt
        user_prompt = version.user_template.format(
            context=context,
            question=question
        )
        
        return system_prompt, user_prompt, version.version_id
    
    def _weighted_random_selection(
        self,
        versions: Dict[str, PromptVersion]
    ) -> PromptVersion:
        """Select version using weighted random sampling for A/B testing"""
        active_versions = [v for v in versions.values() if v.active]
        weights = [v.weight for v in active_versions]
        
        return random.choices(active_versions, weights=weights, k=1)[0]
    
    def add_version(self, domain: str, version: PromptVersion):
        """Add new prompt version"""
        if domain not in self.versions:
            self.versions[domain] = {}
        
        self.versions[domain][version.version_id] = version
    
    def deactivate_version(self, domain: str, version_id: str):
        """Deactivate a prompt version"""
        if domain in self.versions and version_id in self.versions[domain]:
            self.versions[domain][version_id].active = False

prompt_manager = PromptVersionManager()
```

### 3.2 A/B Testing
**File:** `api/services/ab_test_service.py`

Track A/B test results.

```python
from collections import defaultdict
from typing import Dict, List
import json

class ABTestService:
    def __init__(self):
        self.results = defaultdict(lambda: {
            'impressions': 0,
            'total_cost': 0.0,
            'total_tokens': 0,
            'total_latency': 0.0,
            'feedback_scores': []
        })
    
    def record_result(
        self,
        version_id: str,
        cost: float,
        tokens: int,
        latency_ms: float,
        feedback_score: float = None
    ):
        """Record A/B test result for a prompt version"""
        stats = self.results[version_id]
        stats['impressions'] += 1
        stats['total_cost'] += cost
        stats['total_tokens'] += tokens
        stats['total_latency'] += latency_ms
        
        if feedback_score is not None:
            stats['feedback_scores'].append(feedback_score)
    
    def get_report(self, version_ids: List[str]) -> Dict:
        """Generate A/B test comparison report"""
        report = {}
        
        for version_id in version_ids:
            stats = self.results[version_id]
            impressions = stats['impressions']
            
            if impressions == 0:
                continue
            
            report[version_id] = {
                'impressions': impressions,
                'avg_cost': stats['total_cost'] / impressions,
                'avg_tokens': stats['total_tokens'] / impressions,
                'avg_latency_ms': stats['total_latency'] / impressions,
                'avg_feedback': (
                    sum(stats['feedback_scores']) / len(stats['feedback_scores'])
                    if stats['feedback_scores'] else None
                )
            }
        
        return report

ab_test_service = ABTestService()
```

---

## Part 4: MLflow Setup

### 4.1 Deploy MLflow
**File:** `kubernetes/mlops/mlflow-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
  namespace: mlops
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow
  template:
    metadata:
      labels:
        app: mlflow
    spec:
      containers:
      - name: mlflow
        image: ghcr.io/mlflow/mlflow:v2.9.2
        ports:
        - containerPort: 5000
        env:
        - name: MLFLOW_BACKEND_STORE_URI
          value: "postgresql://mlflow:password@postgres:5432/mlflow"
        - name: MLFLOW_DEFAULT_ARTIFACT_ROOT
          value: "s3://llmops-rag-mlflow/artifacts"
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: access-key-id
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: secret-access-key
        command:
          - mlflow
          - server
          - --host
          - 0.0.0.0
          - --port
          - "5000"
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow
  namespace: mlops
spec:
  selector:
    app: mlflow
  ports:
    - port: 5000
      targetPort: 5000
  type: LoadBalancer
```

### 4.2 Experiment Tracking
**File:** `api/mlflow_tracking.py`

Track experiments with MLflow.

```python
import mlflow
import os

# Configure MLflow
mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000'))

def log_query_experiment(
    prompt_version: str,
    model_tier: str,
    domain: str,
    cost: float,
    tokens: dict,
    latency_ms: float,
    cached: bool
):
    """Log query as MLflow experiment"""
    
    with mlflow.start_run(run_name=f"query_{domain}_{model_tier}"):
        # Log parameters
        mlflow.log_param("prompt_version", prompt_version)
        mlflow.log_param("model_tier", model_tier)
        mlflow.log_param("domain", domain)
        mlflow.log_param("cached", cached)
        
        # Log metrics
        mlflow.log_metric("cost", cost)
        mlflow.log_metric("input_tokens", tokens.get('input', 0))
        mlflow.log_metric("output_tokens", tokens.get('output', 0))
        mlflow.log_metric("latency_ms", latency_ms)
        
        # Log tags
        mlflow.set_tag("environment", os.getenv('APP_ENV', 'dev'))
```

### 4.3 Model Registry
**File:** `api/model_registry.py`

Register prompt versions as "models" in MLflow.

```python
import mlflow
from mlflow.models import infer_signature

def register_prompt_version(
    version_id: str,
    domain: str,
    system_prompt: str,
    user_template: str
):
    """Register prompt version in MLflow model registry"""
    
    with mlflow.start_run():
        # Log prompt as artifact
        mlflow.log_text(system_prompt, "system_prompt.txt")
        mlflow.log_text(user_template, "user_template.txt")
        
        # Log as model
        mlflow.pyfunc.log_model(
            artifact_path="prompt",
            python_model=None,  # Prompts are text, not Python models
            registered_model_name=f"prompt_{domain}_{version_id}"
        )
```

---

## Part 5: Evaluation Pipeline

### 5.1 Quality Metrics
**File:** `api/evaluation/metrics.py`

Define quality metrics for RAG evaluation.

```python
from typing import List, Dict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.translate.bleu_score import sentence_bleu

class EvaluationMetrics:
    def __init__(self):
        pass
    
    def relevance_score(
        self,
        answer: str,
        context: str,
        answer_embedding: List[float],
        context_embedding: List[float]
    ) -> float:
        """
        Measure how relevant the answer is to the context.
        Uses cosine similarity of embeddings.
        """
        similarity = cosine_similarity(
            [answer_embedding],
            [context_embedding]
        )[0][0]
        return float(similarity)
    
    def coherence_score(self, answer: str) -> float:
        """
        Measure answer coherence (simple heuristic).
        Checks for complete sentences, proper punctuation.
        """
        sentences = nltk.sent_tokenize(answer)
        
        if not sentences:
            return 0.0
        
        # Check if sentences end with proper punctuation
        proper_endings = sum(
            1 for s in sentences
            if s.strip()[-1] in '.!?'
        )
        
        coherence = proper_endings / len(sentences)
        return coherence
    
    def accuracy_score(
        self,
        answer: str,
        reference_answer: str
    ) -> float:
        """
        Measure accuracy against reference answer using BLEU score.
        """
        reference_tokens = nltk.word_tokenize(reference_answer.lower())
        answer_tokens = nltk.word_tokenize(answer.lower())
        
        bleu = sentence_bleu([reference_tokens], answer_tokens)
        return bleu
    
    def calculate_all(
        self,
        answer: str,
        context: str,
        answer_embedding: List[float],
        context_embedding: List[float],
        reference_answer: str = None
    ) -> Dict[str, float]:
        """Calculate all quality metrics"""
        metrics = {
            'relevance': self.relevance_score(
                answer, context, answer_embedding, context_embedding
            ),
            'coherence': self.coherence_score(answer)
        }
        
        if reference_answer:
            metrics['accuracy'] = self.accuracy_score(answer, reference_answer)
        
        return metrics

evaluator = EvaluationMetrics()
```

### 5.2 Automated Testing
**File:** `api/evaluation/test_suite.py`

Automated evaluation test suite.

```python
from typing import List, Dict
import json
from api.services.rag_service import rag_service
from api.evaluation.metrics import evaluator
from api.services.embedding_service import embedding_service

class EvaluationTestSuite:
    def __init__(self, test_cases_file: str):
        with open(test_cases_file, 'r') as f:
            self.test_cases = json.load(f)
    
    def run_evaluation(self, domain: str = None) -> Dict:
        """Run evaluation on test cases"""
        results = []
        
        for test_case in self.test_cases:
            if domain and test_case.get('domain') != domain:
                continue
            
            question = test_case['question']
            expected_answer = test_case.get('expected_answer')
            test_domain = test_case.get('domain', 'general')
            
            # Get RAG response
            response = rag_service.query(question, domain=test_domain)
            
            # Generate embeddings for evaluation
            answer_embedding = embedding_service.generate_embedding(response['answer'])
            context_embedding = embedding_service.generate_embedding(
                "\\n".join([str(s) for s in response['sources']])
            )
            
            # Calculate metrics
            metrics = evaluator.calculate_all(
                answer=response['answer'],
                context="\\n".join([str(s) for s in response['sources']]),
                answer_embedding=answer_embedding,
                context_embedding=context_embedding,
                reference_answer=expected_answer
            )
            
            results.append({
                'question': question,
                'answer': response['answer'],
                'metrics': metrics,
                'cost': response.get('cost', 0),
                'latency_ms': response.get('execution_time_ms', 0),
                'model_used': response.get('model_used', 'unknown')
            })
        
        return self._generate_report(results)
    
    def _generate_report(self, results: List[Dict]) -> Dict:
        """Generate evaluation report"""
        if not results:
            return {}
        
        avg_metrics = {
            'relevance': np.mean([r['metrics']['relevance'] for r in results]),
            'coherence': np.mean([r['metrics']['coherence'] for r in results]),
            'cost': np.mean([r['cost'] for r in results]),
            'latency_ms': np.mean([r['latency_ms'] for r in results])
        }
        
        if 'accuracy' in results[0]['metrics']:
            avg_metrics['accuracy'] = np.mean([
                r['metrics']['accuracy'] for r in results
            ])
        
        return {
            'summary': avg_metrics,
            'total_tests': len(results),
            'detailed_results': results
        }
```

### 5.3 Evaluation Reports
**File:** `scripts/generate_eval_report.py`

Generate HTML evaluation reports.

```python
import json
from jinja2 import Template
from datetime import datetime

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>RAG Evaluation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .metric-good { color: green; }
        .metric-bad { color: red; }
    </style>
</head>
<body>
    <h1>RAG Evaluation Report</h1>
    <p>Generated: {{ timestamp }}</p>
    
    <h2>Summary Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Average Value</th>
        </tr>
        {% for metric, value in summary.items() %}
        <tr>
            <td>{{ metric }}</td>
            <td>{{ "%.4f"|format(value) }}</td>
        </tr>
        {% endfor %}
    </table>
    
    <h2>Detailed Results</h2>
    <table>
        <tr>
            <th>Question</th>
            <th>Relevance</th>
            <th>Coherence</th>
            <th>Cost ($)</th>
            <th>Latency (ms)</th>
        </tr>
        {% for result in results %}
        <tr>
            <td>{{ result.question[:100] }}...</td>
            <td>{{ "%.2f"|format(result.metrics.relevance) }}</td>
            <td>{{ "%.2f"|format(result.metrics.coherence) }}</td>
            <td>{{ "%.4f"|format(result.cost) }}</td>
            <td>{{ result.latency_ms }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

def generate_report(eval_results: dict, output_file: str):
    template = Template(REPORT_TEMPLATE)
    
    html = template.render(
        timestamp=datetime.now().isoformat(),
        summary=eval_results['summary'],
        results=eval_results['detailed_results']
    )
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Report generated: {output_file}")
```

---

## Part 6: Data Drift Detection

### 6.1 Query Pattern Monitoring
**File:** `api/monitoring/drift_detector.py`

Monitor query distributions for drift.

```python
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from scipy.stats import ks_2samp

class DriftDetector:
    def __init__(self, window_days=7):
        self.window_days = window_days
        self.query_lengths = defaultdict(list)
        self.domain_counts = defaultdict(int)
        self.timestamps = []
    
    def record_query(self, query: str, domain: str):
        """Record query for drift analysis"""
        self.query_lengths[domain].append(len(query.split()))
        self.domain_counts[domain] += 1
        self.timestamps.append(datetime.now())
    
    def detect_drift(self, domain: str) -> dict:
        """
        Detect drift in query patterns using Kolmogorov-Smirnov test.
        Compares current week vs previous week.
        """
        cutoff = datetime.now() - timedelta(days=self.window_days)
        
        # Split data into current and previous windows
        current_window = []
        previous_window = []
        
        for i, ts in enumerate(self.timestamps):
            if ts >= cutoff:
                current_window.append(self.query_lengths[domain][i])
            elif ts >= cutoff - timedelta(days=self.window_days):
                previous_window.append(self.query_lengths[domain][i])
        
        if len(current_window) < 30 or len(previous_window) < 30:
            return {
                'drift_detected': False,
                'reason': 'Insufficient data'
            }
        
        # Perform KS test
        statistic, p_value = ks_2samp(current_window, previous_window)
        
        drift_detected = p_value < 0.05  # 5% significance level
        
        return {
            'drift_detected': drift_detected,
            'p_value': p_value,
            'statistic': statistic,
            'current_mean_length': np.mean(current_window),
            'previous_mean_length': np.mean(previous_window)
        }

drift_detector = DriftDetector()
```

### 6.2 Drift Alerts
**File:** `api/monitoring/drift_alerts.py`

Send alerts when drift is detected.

```python
import boto3
from api.monitoring.drift_detector import drift_detector

sns = boto3.client('sns', region_name='ap-southeast-2')

def check_and_alert_drift(domain: str, topic_arn: str):
    """Check for drift and send SNS alert if detected"""
    result = drift_detector.detect_drift(domain)
    
    if result['drift_detected']:
        message = f"""
Data Drift Detected!

Domain: {domain}
P-value: {result['p_value']:.4f}
Current avg query length: {result['current_mean_length']:.1f} words
Previous avg query length: {result['previous_mean_length']:.1f} words

Action Required: Review query patterns and consider retraining or prompt adjustments.
        """
        
        sns.publish(
            TopicArn=topic_arn,
            Subject=f"Data Drift Alert - {domain}",
            Message=message
        )
```

---

## Part 7: Verification

### 7.1 Verification Steps

**1. Verify Redis Caching**
```bash
# Check cache hit rate
curl http://localhost:9090/api/v1/query?query=rag_cache_hits_total

# Make duplicate queries to test caching
for i in {1..5}; do
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"question": "What is the deployment process?", "domain": "engineering"}'
done

# Verify cache hit rate increased
```

**2. Verify Intelligent Routing**
```bash
# Simple query (should use Lite)
curl -X POST http://localhost:8000/query \
  -d '{"question": "Hi", "domain": "general"}' | jq '.model_used'

# Complex query (should use Pro)
curl -X POST http://localhost:8000/query \
  -d '{"question": "Explain the architectural implications of implementing a distributed consensus algorithm in a microservices environment with eventual consistency requirements", "domain": "engineering"}' | jq '.model_used'
```

**3. Test A/B Testing**
```bash
# Run multiple queries to trigger different prompt versions
python scripts/run_ab_test.py --domain legal --queries 100

# Check MLflow for experiment results
open http://localhost:5000
```

**4. Run Evaluation Suite**
```bash
# Run automated evaluation
python -m api.evaluation.test_suite \
  --test-cases tests/eval_cases.json \
  --output reports/eval_$(date +%Y%m%d).html

# View report
open reports/eval_*.html
```

### 7.2 Verification Checklist

### ✅ Semantic Caching
- [ ] Redis deployed and accessible
- [ ] Embedding cache working
- [ ] Response cache with similarity search functional
- [ ] Cache hit rate metrics visible in Prometheus
- [ ] Cost savings tracked

### ✅ Intelligent Routing
- [ ] Simple queries route to Lite
- [ ] Complex queries route to Pro
- [ ] Domain-specific routing works (legal → Pro)
- [ ] Routing metrics tracked
- [ ] Cost savings measurable

### ✅ Prompt Versioning
- [ ] Multiple prompt versions defined
- [ ] A/B testing distributes traffic
- [ ] Version performance tracked in MLflow
- [ ] Can activate/deactivate versions

### ✅ MLflow
- [ ] MLflow UI accessible
- [ ] Experiments logged automatically
- [ ] Prompt versions in model registry
- [ ] Metrics visible in UI

### ✅ Evaluation
- [ ] Test suite runs successfully
- [ ] Quality metrics calculated
- [ ] Reports generated
- [ ] Regression tests pass

### ✅ Drift Detection
- [ ] Query patterns monitored
- [ ] Drift detection algorithm works
- [ ] Alerts sent when drift detected

---

**Next Strategic Move:** With MLOps capabilities operational, we proceed to **Phase 7: EKS Deployment** to deploy the complete system to AWS and validate the pause/resume architecture for cost optimization.
