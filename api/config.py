"""Configuration settings for the application."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # pylint: disable=too-few-public-methods

    # Application
    app_name: str = "LLMOps RAG Pipeline"
    app_version: str = "0.1.0"
    debug: bool = True

    # AWS
    aws_region: str = "ap-southeast-2"
    documents_bucket: str = "llmops-rag-documents-dev"  # Replace with your bucket
    guardrail_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
