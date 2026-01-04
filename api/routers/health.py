# api/routers/health.py

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    # TODO: Check connections (Redis, Vector DB, AWS)
    return {
        "status": "ready",
        "checks": {
            "api": "ok",
            # "redis": "ok",
            # "vector_db": "ok",
            # "aws": "ok"
        }
    }

@router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}