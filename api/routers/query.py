from fastapi import APIRouter
from pydantic import BaseModel
from api.services.rag_service import rag_service

""" Router for handling RAG queries and domain-specific search """

router = APIRouter()

# Schema for RAG query requests
class QueryRequest(BaseModel):
    question: str
    domain: str = None  # Optional domain for focused retrieval

# Main RAG endpoint combining retrieval and generation
@router.post("/query")
async def query_rag(request: QueryRequest):
    return rag_service.query(request.question, request.domain)