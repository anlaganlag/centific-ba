#!/bin/bash
# ============================================================
# BA Toolkit — Azure Container Apps Deployment Script
# ============================================================
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker images pushed to ACR
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
# ============================================================

set -euo pipefail

# ── Configuration (edit these) ──────────────────────────────
RESOURCE_GROUP="rg-ba-toolkit"
LOCATION="eastus"
ACR_NAME="crswatteam01"
ENVIRONMENT_NAME="cae-ba-toolkit"
BACKEND_APP_NAME="ba-toolkit-backend"
FRONTEND_APP_NAME="ba-toolkit-frontend"

# ── Step 1: Ensure resource group exists ────────────────────
echo "==> Ensuring resource group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none 2>/dev/null || true

# ── Step 2: Ensure Container Apps Environment exists ────────
echo "==> Ensuring Container Apps Environment..."
az containerapp env create \
  --name "$ENVIRONMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none 2>/dev/null || true

# ── Step 3: Build and push images to ACR ────────────────────
echo "==> Building and pushing backend image..."
az acr build \
  --registry "$ACR_NAME" \
  --image ba-toolkit-backend:latest \
  --file backend/Dockerfile \
  backend/

echo "==> Building and pushing frontend image..."
az acr build \
  --registry "$ACR_NAME" \
  --image ba-toolkit-frontend:latest \
  --file frontend/Dockerfile \
  frontend/

# ── Step 4: Deploy backend ──────────────────────────────────
echo "==> Deploying backend..."
az containerapp create \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT_NAME" \
  --image "${ACR_NAME}.azurecr.io/ba-toolkit-backend:latest" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --target-port 8000 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --env-vars \
    AZURE_OPENAI_API_KEY=secretref:azure-openai-key \
    AZURE_OPENAI_ENDPOINT=secretref:azure-openai-endpoint \
    AZURE_OPENAI_DEPLOYMENT=gpt-4o \
    AZURE_OPENAI_API_VERSION=2024-08-01-preview \
    OPENAI_API_KEY=secretref:openai-key \
    JWT_SECRET_KEY=secretref:jwt-secret \
    DOCLING_SERVE_URL=https://docling-serve.nicemoss-edd0d815.eastus.azurecontainerapps.io \
    DATABASE_PATH=data/app.db \
    VECTOR_DB_PATH=data/vectors \
    UPLOAD_DIR=data/uploads \
    CORS_ORIGINS=https://${FRONTEND_APP_NAME}.*.azurecontainerapps.io \
  --output none 2>/dev/null || \
az containerapp update \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "${ACR_NAME}.azurecr.io/ba-toolkit-backend:latest" \
  --output none

BACKEND_FQDN=$(az containerapp show \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)
echo "Backend FQDN: $BACKEND_FQDN"

# ── Step 5: Deploy frontend ────────────────────────────────
echo "==> Deploying frontend..."
az containerapp create \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT_NAME" \
  --image "${ACR_NAME}.azurecr.io/ba-toolkit-frontend:latest" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --output none 2>/dev/null || \
az containerapp update \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --image "${ACR_NAME}.azurecr.io/ba-toolkit-frontend:latest" \
  --output none

FRONTEND_URL=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "============================================================"
echo "  Deployment complete!"
echo "  Frontend: https://$FRONTEND_URL"
echo "  Backend:  https://$BACKEND_FQDN (internal)"
echo "============================================================"
