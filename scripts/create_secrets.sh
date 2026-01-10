#!/bin/bash

# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name rag-api-secrets-prod \
  --description "Production secrets for RAG API" \
  --secret-string '{
    "OPENAI_API_KEY": "placeholder",
    "BEDROCK_GUARDRAIL_ID": "your-guardrail-id",
    "DATABASE_PASSWORD": "your-db-password"
  }' \
  --region ap-southeast-2

echo "Secret created: rag-api-secrets-prod"
