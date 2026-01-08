from fastapi import APIRouter
from pydantic import BaseModel
from api.services.rag_service import rag_service
from api.utils.metrics import RAG_REQUEST_LATENCY
import time

""" Router for handling RAG queries and domain-specific search """

router = APIRouter()


# Schema for RAG query requests
class QueryRequest(BaseModel):
    question: str
    domain: str | None = None  # Optional domain for focused retrieval


# Main RAG endpoint combining retrieval and generation
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
