"""
Unit Tests for RAG Service
Tests the core RAG query flow with mocked dependencies (Vector Store, LLM)
"""

import pytest
from api.services.rag_service import rag_service
from unittest.mock import Mock, patch


@pytest.mark.asyncio
async def test_rag_query_success():
    """Test successful RAG query with mocked dependencies"""

    # Mock the vector store to avoid actual ChromaDB calls
    with patch("api.services.rag_service.vector_store") as mock_vector:
        # Mock the LLM service to avoid actual Bedrock API calls
        with patch("api.services.rag_service.llm_service") as mock_llm:
            # Mock the prompt template function
            with patch("api.services.rag_service.get_prompt") as mock_prompt:

                # Setup: Mock vector search to return test documents
                mock_vector.hybrid_search.return_value = {
                    "documents": ["Test document content"],
                    "metadatas": [{"domain": "test", "source": "test.pdf"}],
                }

                # Setup: Mock prompt generation
                mock_prompt.return_value = (
                    "System: You are a helpful assistant",
                    "User: test question\nContext: Test document content",
                )

                # Setup: Mock LLM to return a canned response
                mock_llm.generate_response.return_value = "Test answer"

                # Execute: Call the actual RAG service
                result = rag_service.query("test question", domain="test")

                # Verify: Check response structure and content
                assert result["answer"] == "Test answer"
                assert result["domain"] == "test"
                assert "execution_time_ms" in result
                assert len(result["sources"]) == 1

                # Verify: Ensure dependencies were called correctly
                mock_vector.hybrid_search.assert_called_once()
                mock_llm.generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_rag_query_with_invalid_domain():
    """Test RAG query with access control (placeholder for future implementation)"""
    # TODO: Implement access control tests when guardrails are added
    pass
