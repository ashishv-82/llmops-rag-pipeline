import boto3
import json
from api.config import settings

""" Wrapper for AWS Bedrock Runtime API """


class BedrockClient:
    # Initialize bedrock-runtime client with configured region
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime", region_name=settings.aws_region
        )

    # Invoke Bedrock model with given model ID and body
    def invoke(self, model_id: str, body: dict) -> dict:
        response = self.client.invoke_model(modelId=model_id, body=json.dumps(body))
        return json.loads(response["body"].read())


# Shared client instance
bedrock_client = BedrockClient()
