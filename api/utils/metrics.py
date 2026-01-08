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
