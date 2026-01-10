"""Service for RAG (Retrieval-Augmented Generation) operations."""

import time
from api.services.vector_store import vector_store
from api.services.llm_service import llm_service
from api.services.embedding_service import embedding_service
from api.services.routing_service import routing_service
from api.services.cache_service import cache_service
from api.prompts.versions import prompt_manager
from api.utils.metrics import track_cost, track_tokens, RAG_REQUEST_LATENCY, CACHE_SAVINGS
from api.utils.mlflow_utils import setup_mlflow, log_query_experiment
from api.monitoring.drift_detector import drift_detector


class RAGService:
    """Orchestrates retrieval and generation for RAG pipeline."""

    # pylint: disable=too-few-public-methods
    
    def __init__(self):
        # Initialize MLflow configuration
        setup_mlflow()

    def query(self, question: str, domain: str | None = None, use_hybrid=True):
        """
        Execute RAG workflow: Retrieve context -> Generate Answer.

        Args:
            question: User query
            domain: Optional domain filter
            use_hybrid: Whether to use hybrid search (Vector + BM25)

        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Record query for drift detection
        drift_detector.record_query(question, domain or 'general')
        
        # Handle 'all' domain for global search (remove filter)
        if domain == "all":
            domain = None
        
        start_time = time.time()

        # 1. Check cache first
        query_embedding = embedding_service.generate_embedding(question)
        
        cached_response = cache_service.find_similar_response(
            question,
            query_embedding,
            domain or 'general'
        )
        
        if cached_response:
            response_text, similarity = cached_response
            
            # Estimate saved cost (avg query cost ~$0.01)
            saved_cost = 0.01
            CACHE_SAVINGS.inc(saved_cost)
            
            execution_time = time.time() - start_time
            
            return {
                "question": question,
                "answer": response_text,
                "cached": True,
                "cache_similarity": similarity,
                "cost": 0.0,
                "cost_saved": saved_cost,
                "execution_time_ms": round(execution_time * 1000, 2),
                "sources": [],
                "domain": domain,
            }
            
            # Log cache hit to MLflow (async/background in production)
            log_query_experiment(
                prompt_version="cached",
                model_tier="cached",
                domain=domain or "general",
                cost=0.0,
                tokens={"input": 0, "output": 0},
                latency_ms=execution_time * 1000,
                cached=True
            )
            
            return {
                "question": question,
                "answer": response_text,
                "cached": True,
                "cache_similarity": similarity,
                "cost": 0.0,
                "cost_saved": saved_cost,
                "execution_time_ms": round(execution_time * 1000, 2),
                # Return empty/default values for other fields
                "sources": [],
                "domain": domain,
            }

        # 2. Determine model tier via routing
        model_tier = routing_service.analyze_complexity(question, domain or 'general')
        # Map tier to actual model ID
        # lite -> global.amazon.nova-2-lite-v1:0
        # pro  -> global.amazon.nova-2-pro-v1:0
        model_id = f"global.amazon.nova-2-{model_tier}-v1:0"

        # 3. Retrieve with hybrid search
        retrieval_start = time.time()
        filters = {"domain": domain} if domain else None
        
        if use_hybrid:
            results = vector_store.hybrid_search(
                question, top_k=3, filter=filters, alpha=0.7  # 70% vector, 30% BM25
            )
        else:
            results = vector_store.search(question, top_k=3, filter=filters)

        context_chunks = results["documents"]
        # sources = results["metadatas"] # Assuming metadatas contains source info
        # Adapting to typical structure: metadatas is list of dicts
        sources = results.get("metadatas", [])
        
        context_text = "\n\n".join(context_chunks)
        
        # Track retrieval latency
        retrieval_duration = time.time() - retrieval_start
        RAG_REQUEST_LATENCY.labels(
            stage="retrieval",
            environment="dev"
        ).observe(retrieval_duration)

        # Get prompt from version manager (handles A/B testing)
        # Fix: 'related_text' was not defined, should use 'context_text'
        system_prompt, user_prompt, version_id = prompt_manager.get_prompt(
            domain=domain or "general",
            context=context_text,
            question=question
        )

        # Generate response using intelligent routing logic
        try:
            # 1. Analyze complexity to choose model tier
            routing_decision = routing_service.analyze_complexity(question, domain or "general")
            model_tier = routing_decision["model_tier"]
            model_id = routing_decision["model_id"]
            
            # 2. Generate response with selected model
            # Note: We pass model_id to generate_response to avoid re-instantiating the service
            response_text = llm_service.generate_response(
                system_prompt=system_prompt,
                prompt=user_prompt,
                model_id=model_id
            )
            
            execution_time = time.time() - start_time
            
            # 3. Cache the new response
            # async/background task in production
            cache_service.set_response(question, query_embedding, response_text, domain or "general")
            
            # Track metrics
            # Estimate tokens - simple approximation for now (4 chars ~= 1 token)
            estimated_input_tokens = len(system_prompt + user_prompt) / 4
            estimated_output_tokens = len(response_text) / 4
            
            self._track_metrics(estimated_input_tokens, estimated_output_tokens, execution_time)

            # Log experiment to MLflow
            log_query_experiment(
                prompt_version=version_id,
                model_tier=model_tier,
                domain=domain or "general",
                cost=(estimated_input_tokens / 1000 * 0.00006) + (estimated_output_tokens / 1000 * 0.00024),
                tokens={"input": int(estimated_input_tokens), "output": int(estimated_output_tokens)},
                latency_ms=execution_time * 1000,
                cached=False
            )

            return {
                "question": question,
                "answer": response_text,
                "cached": False,
                "model_tier": model_tier,
                "prompt_version": version_id,
                "complexity_metrics": routing_decision.get("metrics", {}),
                "cost": (estimated_input_tokens / 1000 * 0.00006) + (estimated_output_tokens / 1000 * 0.00024),
                "execution_time_ms": round(execution_time * 1000, 2),
                "sources": sources,
                "domain": domain,
            }

        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                "question": question,
                "answer": "I recently encountered an error while processing your request. Please try again later.",
                "cached": False,
                "error": str(e)
            }

    def _track_metrics(self, input_tokens, output_tokens, execution_time):
        """Helper to track Prometheus metrics"""
        RAG_REQUEST_LATENCY.labels(
            stage="generation",
            environment="dev"
        ).observe(execution_time)
        
        track_tokens(int(input_tokens), model="bedrock-nova", type="input", env="dev")
        track_tokens(int(output_tokens), model="bedrock-nova", type="output", env="dev")
        
        # Bedrock Nova Lite pricing: $0.00006/1K input tokens, $0.00024/1K output tokens
        cost = (input_tokens / 1000 * 0.00006) + (output_tokens / 1000 * 0.00024)
        track_cost(cost, model="bedrock-nova", env="dev")
