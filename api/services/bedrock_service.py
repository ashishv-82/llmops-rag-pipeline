"""Wrapper for AWS Bedrock Runtime API."""

import json
import boto3
from api.config import settings


class BedrockClient:
    """Client for invoking AWS Bedrock models."""

    # pylint: disable=too-few-public-methods

    def __init__(self):
        """Initialize bedrock-runtime client with configured region."""
        self.client = boto3.client(
            service_name="bedrock-runtime", region_name=settings.aws_region
        )

    def invoke(self, model_id: str, body: dict) -> dict:
        """
        Invoke Bedrock model with given model ID and body.

        Args:
            model_id: The ID of the model to invoke
            body: The JSON body payload

        Returns:
            The parsed JSON response body
        """
        response = self.client.invoke_model(modelId=model_id, body=json.dumps(body))
        return json.loads(response["body"].read())


# Shared client instance
bedrock_client = BedrockClient()
