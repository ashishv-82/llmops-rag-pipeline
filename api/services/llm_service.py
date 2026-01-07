"""Service for handling text generation via Amazon Bedrock."""

from api.services.bedrock_service import bedrock_client
from api.config import settings


class LLMService:
    """Service for handling text generation via Amazon Bedrock."""

    # pylint: disable=too-few-public-methods

    def __init__(self, model_id="global.amazon.nova-2-lite-v1:0"):
        self.model_id = model_id
        # Check if Bedrock Guardrails are enabled
        self.use_guardrails = hasattr(settings, "guardrail_id")

    def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate a response using the configured LLM.

        Args:
            prompt: User input prompt
            system_prompt: Optional system context

        Returns:
            Generated text response
        """
        # Format request body for Nova 2 model
        # System prompt must be a top-level parameter, not in messages
        body = {
            "inferenceConfig": {"max_new_tokens": 1000},
            "system": [{"text": system_prompt}],
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
        }

        # Apply safety guardrails if configured
        if self.use_guardrails:
            body["guardrailIdentifier"] = settings.guardrail_id
            body["guardrailVersion"] = "DRAFT"

        try:
            # Invoke model and extract generated text
            response = bedrock_client.invoke(self.model_id, body)
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            return f"Error invoking model: {str(e)}"


# Singleton instance
llm_service = LLMService()
