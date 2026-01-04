# MLOps Folder Structure and Functionality

## Overview

The `mlops/` folder contains components for operating, monitoring, and continuously improving the RAG system. These tools enable experiment tracking, quality evaluation, cost optimization, and data drift detection.

---

## Folder Structure

```
mlops/
├── data_pipeline/              # Data processing
│   ├── ingest.py               # Document ingestion
│   └── preprocess.py           # Text preprocessing
│
├── monitoring/                 # Custom metrics
│   ├── metrics_collector.py    # Collect custom metrics
│   ├── cost_tracker.py         # Cost per query tracking
│   └── drift_detection.py      # Data drift detection
│
├── evaluation/                 # LLM evaluation
│   ├── quality_metrics.py      # Response quality assessment
│   └── prompt_testing.py       # Prompt A/B testing
│
└── experiments/                # MLflow tracking
    └── mlflow_tracking.py      # Experiment tracking
```

---

## Data Pipeline

### `data_pipeline/ingest.py` - Document Ingestion

**Purpose:** Handle document ingestion from both web UI and GitHub Actions

**Responsibilities:**

**Document Processing:**
- Accept documents from dual paths:
  - Path 1: Web UI uploads (handled by API)
  - Path 2: GitHub Actions (automated sync)
- Validate file format (PDF, TXT, DOCX)
- Validate file size limits
- Extract metadata (filename, size, upload date)

**Text Extraction:**
- PDF: Extract text using PyPDF
- DOCX: Extract text using python-docx
- TXT: Read directly
- Handle encoding issues
- Preserve formatting where relevant

**Metadata Enrichment:**
- Auto-detect document type
- Extract domain from filename or content
- Generate document ID
- Add timestamps
- Tag with source (web-ui or github-actions)

**Storage:**
- Upload original file to S3
- Store metadata in database
- Trigger embedding generation pipeline

**Error Handling:**
- Corrupted files
- Unsupported formats
- Size limit exceeded
- S3 upload failures

**Metrics Tracked:**
- Documents ingested per day
- Success/failure rates
- Processing time
- Storage used

**Used in:** Phase 3 (Core Features)

---

### `data_pipeline/preprocess.py` - Text Preprocessing

**Purpose:** Clean and prepare text for optimal embedding quality

**Preprocessing Steps:**

**Text Cleaning:**
- Remove extra whitespace
- Normalize line breaks
- Remove special characters (configurable)
- Handle different encodings (UTF-8, Latin-1, etc.)
- Remove headers/footers (for PDFs)

**Text Normalization:**
- Lowercase conversion (optional)
- Remove accents and diacritics
- Expand contractions ("don't" → "do not")
- Normalize numbers and dates

**Structure Preservation:**
- Identify section headers
- Preserve bullet points and lists
- Maintain paragraph boundaries
- Keep table structures (where possible)

**Domain-Specific Processing:**
- Legal: Preserve citations, section numbers
- HR: Preserve policy numbers, effective dates
- Technical: Preserve code blocks, formulas

**Output:**
- Clean, normalized text
- Preserved structure metadata
- Ready for chunking

**Used in:** Phase 3 (Core Features)

---

## Monitoring

### `monitoring/metrics_collector.py` - Custom Metrics

**Purpose:** Collect application-specific metrics beyond standard Prometheus

**Metrics Collected:**

**Query Metrics:**
- Queries per minute/hour/day
- Queries by domain (HR, Legal, etc.)
- Query complexity distribution
- Average query length
- Unique vs repeat queries

**Document Metrics:**
- Total documents in system
- Documents by domain
- Document usage frequency
- Unused documents (never retrieved)
- Document age distribution

**User Behavior:**
- Active users
- Queries per user
- Peak usage times
- Domain preferences
- Query patterns

**System Health:**
- API response times
- Cache hit rates
- Vector DB query latency
- LLM API latency
- Error rates by type

**Integration:**
- Sends metrics to Prometheus
- Visualized in Grafana dashboards
- Alerts on anomalies

**Used in:** Phase 5 (Monitoring)

---

### `monitoring/cost_tracker.py` - Cost Per Query Tracking

**Purpose:** Track and optimize costs for every query

**Cost Components Tracked:**

**LLM Costs:**
- Nova 2 Lite: $X per 1K tokens
- Nova 2 Pro: $Y per 1K tokens
- Input tokens vs output tokens
- Cost per query
- Daily/weekly/monthly totals

**Embedding Costs:**
- Titan Embeddings V2: $Z per 1K tokens
- Document embedding costs
- Query embedding costs
- Total embedding spend

**Infrastructure Costs:**
- EKS cluster costs (allocated per query)
- S3 storage costs
- Redis cache costs
- Data transfer costs

**Cost Savings Tracked:**

**From Semantic Caching:**
- Cache hit rate
- Queries served from cache
- LLM API calls avoided
- Cost saved per day/week/month
- ROI of caching

**From Intelligent Routing:**
- Queries routed to Lite vs Pro
- Cost difference (Pro - Lite)
- Savings from routing
- Quality maintained

**From Optimization:**
- Token reduction strategies
- Chunk size optimization
- Context window optimization

**Reporting:**

**Real-time:**
- Cost per query (displayed to user)
- Running total for the day
- Budget alerts

**Dashboards:**
- Cost trends over time
- Cost breakdown by service
- Cost by domain
- Optimization impact

**Exports:**
- CSV reports for finance
- AWS Cost Explorer integration
- Budget vs actual tracking

**Alerts:**
- Daily budget exceeded
- Unusual cost spike
- Cost anomaly detection

**Used in:** Phase 5 (Monitoring) & Phase 6 (MLOps)

---

### `monitoring/drift_detection.py` - Data Drift Detection

**Purpose:** Monitor changes in query patterns and document relevance

**Drift Types Monitored:**

**Query Distribution Drift:**
- Track query distribution by domain over time
- Detect shifts (e.g., HR queries increasing)
- Alert when distribution changes significantly
- Example: HR queries went from 30% → 50%

**Query Content Drift:**
- Track new query types
- Detect emerging topics
- Identify queries not covered by documents
- Example: Sudden increase in "remote work" queries

**Document Relevance Drift:**
- Track retrieval quality over time
- Monitor if documents are becoming less relevant
- Detect when new documents are needed
- Example: Old policy documents no longer match queries

**Seasonal Patterns:**
- Identify recurring patterns
- Tax season → Finance queries increase
- Year-end → HR policy queries increase
- Adjust expectations accordingly

**Detection Methods:**

**Statistical Tests:**
- Kolmogorov-Smirnov test for distribution changes
- Chi-square test for categorical drift
- Z-score for anomaly detection

**Thresholds:**
- Configurable sensitivity
- Alert levels (warning, critical)
- Minimum sample size requirements

**Actions on Drift:**

**Alerts:**
- Notify team of significant drift
- Recommend adding new documents
- Suggest retraining/updating

**Automatic:**
- Trigger document review
- Update monitoring dashboards
- Log for analysis

**Reports:**
- Weekly drift summary
- Trend analysis
- Recommendations

**Used in:** Phase 6 (MLOps)

---

## Evaluation

### `evaluation/quality_metrics.py` - Response Quality Assessment

**Purpose:** Automated evaluation of RAG system response quality

**Quality Dimensions:**

**Relevance:**
- Does the answer address the question?
- Are retrieved documents relevant?
- Scoring: 0-1 scale

**Accuracy:**
- Is the information factually correct?
- Does it match source documents?
- No hallucinations?
- Scoring: 0-1 scale

**Coherence:**
- Is the response well-structured?
- Logical flow?
- Grammar and readability?
- Scoring: 0-1 scale

**Completeness:**
- Does it cover all aspects of the question?
- Are important details included?
- Scoring: 0-1 scale

**Citation Quality:**
- Are sources properly cited?
- Are citations accurate?
- Scoring: 0-1 scale

**Evaluation Methods:**

**Ground Truth Comparison:**
- Maintain test dataset of Q&A pairs
- Compare generated answers to expected answers
- Calculate similarity scores
- Track accuracy over time

**LLM-as-Judge:**
- Use Nova 2 Pro to evaluate responses
- Provide rubric and scoring criteria
- Get detailed feedback
- More nuanced than simple similarity

**Automated Metrics:**
- BLEU score (text similarity)
- ROUGE score (overlap)
- BERTScore (semantic similarity)
- Perplexity

**Human Evaluation:**
- Sample responses for manual review
- Collect user feedback
- Rating system (1-5 stars)
- Qualitative feedback

**Regression Detection:**
- Track quality metrics over time
- Alert if quality drops below threshold
- Compare before/after changes
- Prevent quality degradation

**Quality Gates:**

**CI/CD Integration:**
- Run evaluation on every deployment
- Block deployment if quality < 0.8
- Automated testing in pipeline

**Continuous Monitoring:**
- Daily evaluation runs
- Track quality trends
- Early warning system

**Reporting:**
- Quality dashboard
- Trend analysis
- Per-domain quality scores
- Improvement recommendations

**Used in:** Phase 6 (MLOps)

---

### `evaluation/prompt_testing.py` - Prompt A/B Testing

**Purpose:** Compare different prompt strategies to optimize quality and cost

**A/B Testing Framework:**

**Test Setup:**
- Define prompt variants (A, B, C, etc.)
- Set traffic split (e.g., 33% each)
- Define success metrics
- Set minimum sample size
- Set test duration

**Prompt Variants:**

**Example Test: Domain-Specific Prompts**
- Variant A: Generic prompt
  ```
  "Answer the question based on context."
  ```
- Variant B: Domain-specific prompt
  ```
  "You are an HR assistant. Provide friendly, policy-based answers."
  ```
- Variant C: Few-shot examples
  ```
  "Here are examples of good answers: ..."
  ```

**Traffic Routing:**
- Random assignment to variants
- Track which variant served each query
- Ensure even distribution
- Handle edge cases

**Metrics Tracked:**

**Quality Metrics:**
- Response relevance score
- User satisfaction (if available)
- Citation accuracy
- Coherence score

**Cost Metrics:**
- Tokens used (input + output)
- Cost per query
- Total cost per variant

**Performance Metrics:**
- Response latency
- Cache hit rate
- Error rate

**Statistical Analysis:**

**Significance Testing:**
- Calculate p-values
- Determine statistical significance
- Minimum sample size requirements
- Confidence intervals

**Winner Selection:**
- Quality improvement > 5%
- Cost reduction > 10%
- No significant latency increase
- Statistical significance achieved

**Reporting:**

**Real-time Dashboard:**
- Current metrics per variant
- Sample size
- Statistical significance
- Projected winner

**Final Report:**
- Detailed comparison
- Recommendation
- Rollout plan
- Expected impact

**Rollout:**

**Gradual Rollout:**
- Winner → 10% traffic
- Monitor for issues
- Increase to 50%
- Full rollout if stable

**Rollback Plan:**
- Automated rollback on errors
- Manual rollback option
- Preserve previous variant

**Used in:** Phase 6 (MLOps)

---

## Experiments

### `experiments/mlflow_tracking.py` - Experiment Tracking

**Purpose:** Track all experiments and configurations using MLflow

**What Gets Tracked:**

**Parameters:**
- Chunk size (500, 1000, 1500)
- Chunk overlap (100, 200, 300)
- LLM model (Nova Lite, Nova Pro)
- Embedding model (Titan V2)
- Retrieval-k (3, 5, 10)
- Domain filter settings
- Prompt version
- Cache threshold
- Routing strategy

**Metrics:**
- Response quality score (0-1)
- Average latency (seconds)
- Cost per query ($)
- Cache hit rate (%)
- Token usage (input/output)
- Error rate (%)
- User satisfaction (if available)

**Artifacts:**
- Prompt templates (text files)
- Configuration files (YAML/JSON)
- Evaluation results (CSV)
- Sample responses (JSON)
- Model outputs (text)

**Experiment Workflow:**

**1. Start Experiment:**
```python
with mlflow.start_run(run_name="chunk-size-experiment"):
    mlflow.log_param("chunk_size", 1000)
    mlflow.log_param("chunk_overlap", 200)
```

**2. Run Evaluation:**
```python
quality_score = evaluate_system()
mlflow.log_metric("quality", quality_score)
```

**3. Log Artifacts:**
```python
mlflow.log_artifact("prompt_template.txt")
mlflow.log_artifact("results.csv")
```

**4. Compare Experiments:**
- View all runs in MLflow UI
- Compare metrics side-by-side
- Filter by parameters
- Find best configuration

**Experiment Types:**

**Configuration Tuning:**
- Test different chunk sizes
- Optimize retrieval-k
- Tune cache threshold

**Model Comparison:**
- Nova Lite vs Pro
- Different embedding models
- Routing strategies

**Prompt Optimization:**
- Generic vs domain-specific
- Few-shot vs zero-shot
- Different prompt structures

**Feature Testing:**
- With/without caching
- With/without domain filtering
- Different hybrid search weights

**MLflow UI:**
- Web interface for viewing experiments
- Compare runs visually
- Search and filter
- Export results

**Integration:**

**CI/CD:**
- Log every deployment as a run
- Track production metrics
- Compare to previous versions

**Continuous Improvement:**
- Regular experimentation
- Data-driven decisions
- Reproducible results

**Used in:** Phase 6 (MLOps)

---

## How These Components Work Together

### Continuous Improvement Cycle

```
1. experiments/mlflow_tracking.py
   → Start new experiment (chunk_size=1000)
   
2. evaluation/quality_metrics.py
   → Evaluate quality (score: 0.85)
   → Log to MLflow
   
3. monitoring/cost_tracker.py
   → Track costs ($0.002/query)
   → Log to MLflow
   
4. experiments/mlflow_tracking.py
   → Compare with previous experiments
   → Identify best configuration
   
5. evaluation/prompt_testing.py
   → A/B test new prompt
   → Variant B wins (quality +8%, cost -5%)
   
6. monitoring/drift_detection.py
   → Detect query pattern shift
   → Alert: "HR queries increased 20%"
   
7. data_pipeline/ingest.py
   → Add new HR documents
   → Process and embed
   
8. evaluation/quality_metrics.py
   → Re-evaluate quality
   → Quality improved to 0.92
   
9. experiments/mlflow_tracking.py
   → Log improved metrics
   → Document changes
```

---

## Implementation Phases

**Phase 3: Core Features**
- `data_pipeline/ingest.py`
- `data_pipeline/preprocess.py`

**Phase 5: Monitoring**
- `monitoring/metrics_collector.py`
- `monitoring/cost_tracker.py`

**Phase 6: MLOps/LLMOps**
- `monitoring/drift_detection.py`
- `evaluation/quality_metrics.py`
- `evaluation/prompt_testing.py`
- `experiments/mlflow_tracking.py`

---

## Key Benefits

### Operational Excellence
- Real-time cost tracking
- Quality monitoring
- Drift detection
- Proactive alerts

### Continuous Improvement
- A/B testing framework
- Experiment tracking
- Data-driven decisions
- Reproducible results

### Production Readiness
- Automated evaluation
- Quality gates in CI/CD
- Comprehensive observability
- Cost optimization

### Portfolio Value
- Demonstrates MLOps expertise
- Shows operational maturity
- Proves cost consciousness
- Interview talking points

---

This `mlops/` folder transforms the project from a simple demo into a **production-grade, continuously improving system** that demonstrates deep understanding of ML operations.
