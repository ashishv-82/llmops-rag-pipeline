import boto3

def create_guardrail():
    client = boto3.client('bedrock', region_name='ap-southeast-2')
    
    response = client.create_guardrail(
        name='rag-content-filter',
        description='PII masking and content filtering for RAG',
        # Safety filters
        contentPolicyConfig={
            'filtersConfig': [
                {'type': 'SEXUAL', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
                {'type': 'VIOLENCE', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
                {'type': 'HATE', 'inputStrength': 'HIGH', 'outputStrength': 'HIGH'},
                {'type': 'INSULTS', 'inputStrength': 'MEDIUM', 'outputStrength': 'MEDIUM'},
            ]
        },
        # PII protection
        sensitiveInformationPolicyConfig={
            'piiEntitiesConfig': [
                {'type': 'EMAIL', 'action': 'ANONYMIZE'},
                {'type': 'PHONE', 'action': 'ANONYMIZE'},
                {'type': 'SSN', 'action': 'BLOCK'},
            ]
        },
        # Topic boundaries
        topicPolicyConfig={
            'topicsConfig': [
                {
                    'name': 'Financial Advice',
                    'definition': 'Investment or financial planning advice',
                    'type': 'DENY'
                }
            ]
        }
    )
    
    # Required for API configuration
    print(f"Guardrail created: {response['guardrailId']}")
    print(f"Add to .env: GUARDRAIL_ID={response['guardrailId']}")

if __name__ == "__main__":
    create_guardrail()