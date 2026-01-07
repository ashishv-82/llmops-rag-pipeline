# api/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "LLMOps RAG Pipeline"
    app_version: str = "0.1.0"
    debug: bool = True

    # AWS
    aws_region: str = "ap-southeast-2"
    documents_bucket: str = "llmops-rag-documents-dev"  # Replace with your bucket

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
