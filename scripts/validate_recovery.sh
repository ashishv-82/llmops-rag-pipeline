#!/bin/bash
set -e

# Get Ingress URL
echo "🔍 Detecting RAG API Endpoint..."
INGRESS_HOST=$(kubectl get svc rag-api-service -n prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

if [ -z "$INGRESS_HOST" ]; then
    echo "⚠️  Ingress not found or not provisioned! Falling back to checking internal service port forward."
    # Optional: Port forward check logic
    # But for external verification we need the URL.
    echo "Using placeholder http://localhost:8000 for local test."
    API_URL="http://localhost:8000"
else
    API_URL="http://$INGRESS_HOST"
fi

echo "🧪 Running Integration Tests against: $API_URL"
echo "Installing dependencies..."
pip install requests -q

python3 tests/integration/test_api_integration.py --url "$API_URL"
