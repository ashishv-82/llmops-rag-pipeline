"""Service for converting text to vector embeddings using Titan V2."""

from typing import List
from api.services.bedrock_service import bedrock_client


class EmbeddingService:
    """Handles interaction with Amazon Titan Embedding models."""

    # pylint: disable=too-few-public-methods

    # Initialize with default Titan V2 embedding model
    def __init__(self, model_id="amazon.titan-embed-text-v2:0"):
        self.model_id = model_id

    # Convert text into a 1024-dimensional vector
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for given text.

        Args:
            text: Input string

        Returns:
            List of floats representing the embedding vector
        """
        body = {"inputText": text, "dimensions": 1024, "normalize": True}
        response = bedrock_client.invoke(self.model_id, body)
        return response["embedding"]


# Shared instance for embedding generation
embedding_service = EmbeddingService()
