#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔌 Establishing connection to Grafana Monitoring Stack...${NC}"
echo -e "${BLUE}ℹ️  This command runs in the foreground. Press Ctrl+C to stop it.${NC}"

# Check if port 3200 is already in use
if lsof -Pi :3200 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${BLUE}⚠️  Port 3200 is already in use. Killing old process...${NC}"
    kill $(lsof -Pi :3200 -sTCP:LISTEN -t)
fi

echo -e "${GREEN}✅ Ready! Grafana is accessible at: http://localhost:3200${NC}"
echo -e "   👤 User:     admin"
echo -e "   🔑 Password: admin"
echo ""

# Run port-forward in foreground
kubectl port-forward svc/prometheus-grafana 3200:80 -n monitoring
