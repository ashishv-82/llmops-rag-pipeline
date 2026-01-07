"""Service for RAG (Retrieval-Augmented Generation) operations."""

import time
from api.services.vector_store import vector_store
from api.services.llm_service import llm_service
from api.prompts.templates import get_prompt


class RAGService:
    """Orchestrates retrieval and generation for RAG pipeline."""

    # pylint: disable=too-few-public-methods

    def query(self, question: str, domain: str = None, use_hybrid=True):
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

        # 1. Retrieve with hybrid search
        filters = {"domain": domain} if domain else None

        if use_hybrid:
            results = vector_store.hybrid_search(
                question, top_k=3, filter=filters, alpha=0.7  # 70% vector, 30% BM25
            )
        else:
            results = vector_store.search(question, top_k=3, filter=filters)

        context_chunks = results["documents"]
        context_text = "\n\n".join(context_chunks)

        # 2. Get domain-specific prompts
        system_prompt, user_prompt = get_prompt(
            domain or "general", context_text, question
        )

        # 3. Generate with guardrails
        answer = llm_service.generate_response(user_prompt, system_prompt)

        execution_time = time.time() - start_time

        return {
            "question": question,
            "answer": answer,
            "sources": results["metadatas"],
            "domain": domain,
            "execution_time_ms": round(execution_time * 1000, 2),
        }


rag_service = RAGService()
