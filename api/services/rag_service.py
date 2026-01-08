"""Service for RAG (Retrieval-Augmented Generation) operations."""

import time
from api.services.vector_store import vector_store
from api.services.llm_service import llm_service
from api.services.embedding_service import embedding_service
from api.services.routing_service import routing_service
from api.services.cache_service import cache_service
from api.prompts.templates import get_prompt
from api.utils.metrics import track_cost, track_tokens, RAG_REQUEST_LATENCY, CACHE_SAVINGS


class RAGService:
    """Orchestrates retrieval and generation for RAG pipeline."""

    # pylint: disable=too-few-public-methods

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
        context_text = "\n\n".join(context_chunks)
        
        # Track retrieval latency
        retrieval_duration = time.time() - retrieval_start
        RAG_REQUEST_LATENCY.labels(
            stage="retrieval",
            environment="dev"
        ).observe(retrieval_duration)

        # 2. Get domain-specific prompts
        system_prompt, user_prompt = get_prompt(
            domain or "general", context_text, question
        )

        # 5. Generate with guardrails and selected model
        generation_start = time.time()
        answer = llm_service.generate_response(user_prompt, system_prompt, model_id=model_id)
        
        # Cache the response
        cache_service.set_response(
            question,
            query_embedding,
            answer,
            domain or 'general'
        )
        
        # Track generation latency
        generation_duration = time.time() - generation_start
        RAG_REQUEST_LATENCY.labels(
            stage="generation",
            environment="dev"
        ).observe(generation_duration)

        execution_time = time.time() - start_time
        
        # Track cost and tokens (placeholder values - will be replaced with actual LLM response data)
        # TODO: Extract actual token counts from llm_service response
        estimated_input_tokens = len(user_prompt.split()) * 1.3  # Rough estimate
        estimated_output_tokens = len(answer.split()) * 1.3
        
        track_tokens(int(estimated_input_tokens), model="bedrock-nova", type="input", env="dev")
        track_tokens(int(estimated_output_tokens), model="bedrock-nova", type="output", env="dev")
        
        # Bedrock Nova Lite pricing: $0.00006/1K input tokens, $0.00024/1K output tokens
        cost = (estimated_input_tokens / 1000 * 0.00006) + (estimated_output_tokens / 1000 * 0.00024)
        track_cost(cost, model="bedrock-nova", env="dev")

        return {
            "question": question,
            "answer": answer,
            "sources": results["metadatas"],
            "domain": domain,
            "model_used": model_tier,
            "cached": False,
            "execution_time_ms": round(execution_time * 1000, 2),
        }


rag_service = RAGService()
