#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
NAMESPACE=$ENVIRONMENT

echo "Deploying to EKS - Environment: $ENVIRONMENT"

# Check dependencies
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl could not be found"
    exit 1
fi

# Ensure namespace exists
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
if [ "$ENVIRONMENT" == "prod" ]; then
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace mlops --dry-run=client -o yaml | kubectl apply -f -
fi

echo "Applying manifests..."

# Apply ConfigMaps
kubectl apply -f kubernetes/base/configmap.yaml -n $NAMESPACE

# Apply Secrets Strategy
if [ "$ENVIRONMENT" == "prod" ]; then
    echo "Applying Production Secrets (External Secrets Operator)..."
    kubectl apply -f kubernetes/base/secret-store.yaml -n $NAMESPACE
    kubectl apply -f kubernetes/base/external-secret.yaml -n $NAMESPACE
    
    # Apply Time-Based Auto-Scaling
    echo "Applying Auto-Scaling Policies..."
    kubectl apply -f kubernetes/base/scheduled-scaler.yaml -n $NAMESPACE
else
    # Dev/Local: Use static secrets
    if [ -f "kubernetes/base/secrets.yaml" ]; then
        echo "Applying Dev Secrets..."
        kubectl apply -f kubernetes/base/secrets.yaml -n $NAMESPACE
    fi
fi

# Deploy Redis
kubectl apply -f kubernetes/base/redis-deployment.yaml -n $NAMESPACE

# Deploy Vector DB
kubectl apply -f kubernetes/base/vectordb-deployment.yaml -n $NAMESPACE

# Deploy API
kubectl apply -f kubernetes/base/deployment.yaml -n $NAMESPACE
kubectl apply -f kubernetes/base/service.yaml -n $NAMESPACE

# Deploy Ingress (if exists)
if [ -f "kubernetes/base/ingress.yaml" ]; then
    kubectl apply -f kubernetes/base/ingress.yaml -n $NAMESPACE
fi

# Deploy Frontend (if exists)
if [ -f "kubernetes/base/frontend-deployment.yaml" ]; then
    kubectl apply -f kubernetes/base/frontend-deployment.yaml -n $NAMESPACE
fi

# Deploy Monitoring (only in proper envs or if requested)
if [ -d "kubernetes/monitoring/" ]; then
    kubectl apply -f kubernetes/monitoring/ -n monitoring
fi

# Deploy MLflow (MLOps)
if [ -d "kubernetes/mlops/" ]; then
    kubectl apply -f kubernetes/mlops/ -n mlops
fi

# Wait for deployments
echo "Waiting for rollout..."
kubectl rollout status deployment/rag-api -n $NAMESPACE --timeout=5m
kubectl rollout status deployment/redis -n $NAMESPACE --timeout=5m

echo "Deployment complete!"
