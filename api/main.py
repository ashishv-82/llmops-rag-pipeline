from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.routers import health, documents, query

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-based Q&A system with MLOps best practices"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(query.router, tags=["query"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to LLMOps RAG Pipeline",
        "version": settings.app_version,
        "docs": "/docs"
    }

@app.on_event("startup")
async def startup_event():
    print("Application startup complete.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)