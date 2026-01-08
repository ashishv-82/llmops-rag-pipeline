import pytest
from api.services.rag_service import RAGService
from unittest.mock import Mock, patch


def test_rag_query_success():
    """Test successful RAG query with mocked dependencies"""
    
    # Mock setup_mlflow to prevent side effects during init
    with patch("api.services.rag_service.setup_mlflow"):
        # Instantiate service for testing
        rag_service = RAGService()
    
    # Mock all external services used in RAGService
    with patch("api.services.rag_service.embedding_service") as mock_embedding, \
         patch("api.services.rag_service.cache_service") as mock_cache, \
         patch("api.services.rag_service.routing_service") as mock_routing, \
         patch("api.services.rag_service.prompt_manager") as mock_prompts, \
         patch("api.services.rag_service.llm_service") as mock_llm, \
         patch("api.services.rag_service.log_query_experiment") as mock_mlflow:

        # 1. Mock Embedding Service
        mock_embedding.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        # 2. Mock Cache Service (Cache Miss)
        mock_cache.get_embedding.return_value = None
        mock_cache.find_similar_response.return_value = None
        
        # 3. Mock Hybrid Search (Vector Store via RAGService instance if not directly mocked)
        # Note: RAGService accesses vector_store directly or via property. 
        # For this test, we might need to patch the vector_store on the instance or globally if it's imported.
        # Looking at rag_service.py, it imports `from api.services.vector_service import vector_store` (implicit or similar)
        # Let's check imports. It uses `self.vector_store` initialized in __init__ or similar.
        # Actually in recent code it was `from api.services.vector_service import vector_store` ? 
        # Let's just patch the object on the instance for safety if possible, or global patch.
        # The original test patched `api.services.rag_service.vector_store`
        
        with patch("api.services.rag_service.vector_store") as mock_vector:
            mock_vector.hybrid_search.return_value = {
                "documents": ["Test document content"],
                "metadatas": [{"domain": "test", "source": "test.pdf"}],
            }

            # 4. Mock Routing Service
            mock_routing.analyze_complexity.return_value = {
                "model_tier": "lite",
                "model_id": "nova-lite-v1",
                "metrics": {"complexity": "low"}
            }
            
            # 5. Mock Prompt Manager
            mock_prompts.get_prompt.return_value = (
                "System Prompt",
                "User Prompt",
                "test_version_v1"
            )
            
            # 6. Mock LLM Service
            mock_llm.generate_response.return_value = "Test response from LLM"

            # Execute
            result = rag_service.query("test question", domain="test")

            # Verify response
            assert result["answer"] == "Test response from LLM"
            assert result["domain"] == "test"
            assert result["model_tier"] == "lite"
            assert result["prompt_version"] == "test_version_v1"
            assert result["cached"] is False
            
            # Verify interactions
            mock_embedding.generate_embedding.assert_called()
            # mock_cache.get_embedding.assert_called() # Not called directly by rag_service
            mock_routing.analyze_complexity.assert_called_with("test question", "test")
            mock_prompts.get_prompt.assert_called()
            mock_llm.generate_response.assert_called()
            mock_cache.set_response.assert_called() # Should cache the new response
            mock_mlflow.assert_called() # Should log experiment


@pytest.mark.asyncio
async def test_rag_query_with_invalid_domain():
    """Test RAG query with access control (placeholder for future implementation)"""
    pass
