#!/bin/bash

# Script to build and deploy the Docker image for the Gemini ADK Demo (FastAPI Backend)

# --- Configuration ---
# Default to production environment
ENV="p"
if [ "$1" == "--dev" ]; then
  ENV="d"
fi

# Load environment variables based on the environment
if [ "$ENV" == "d" ]; then
  ENV_FILE=".env.dev"
  SERVICE_NAME="gemini-adk-demo-d"
else
  ENV_FILE=".env"
  SERVICE_NAME="gemini-adk-demo-p"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE_PATH="${SCRIPT_DIR}/${ENV_FILE}"

if [ -f "${ENV_FILE_PATH}" ]; then
  echo "Sourcing environment variables from ${ENV_FILE_PATH}"
  set -a
  source "${ENV_FILE_PATH}"
  set +a
else
  echo "ERROR: ${ENV_FILE} file not found at ${ENV_FILE_PATH}. Cannot proceed."
  exit 1
fi

# --- GCP Settings ---
PROJECT_ID="${GCP_PROJECT_ID}"
REGION="${GCP_REGION}"

# --- Construct ENV_VARS string for gcloud ---
ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
ENV_VARS+=",GOOGLE_CLOUD_LOCATION=${REGION}"
ENV_VARS+=",GOOGLE_API_KEY=${LLM_API_KEY}"
ENV_VARS+=",CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME}"
ENV_VARS+=",CLOUD_SQL_USER=${CLOUD_SQL_USER}"
ENV_VARS+=",CLOUD_SQL_PASSWORD=${CLOUD_SQL_PASSWORD}"
ENV_VARS+=",CLOUD_SQL_DATABASE_NAME=${CLOUD_SQL_DATABASE_NAME}"
ENV_VARS+=",PRIVATE_IP=${PRIVATE_IP}"

# --- Deployment ---
echo "Deploying ${SERVICE_NAME} to Cloud Run in project ${PROJECT_ID}..."
if [ "$ENV" == "p" ]; then
  read -p "Are you sure you want to proceed with PROD deployment? (y/N): " confirmation
  if [[ "$confirmation" != "y" ]] && [[ "$confirmation" != "Y" ]]; then
    echo "Deployment cancelled."
    exit 0
  fi
fi

# Navigate to the directory of this script (and Dockerfile)
cd "$(dirname "$0")" || exit

gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --port 8080 \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --cpu=1 \
    --memory=2Gi \
    --min-instances=0 \
    --max-instances=2 \
    --timeout=300s \
    --concurrency=10 \
    --allow-unauthenticated \
    --add-cloudsql-instances "${CLOUD_SQL_CONNECTION_NAME}" \
    --set-env-vars="${ENV_VARS}"

if [ $? -eq 0 ]; then
  SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --platform=managed --region=${REGION} --project=${PROJECT_ID} --format='value(status.url)')
  echo "Service '${SERVICE_NAME}' deployed successfully."
  echo "Service URL: ${SERVICE_URL}"
else
  echo "ERROR: Deployment failed."
  exit 1
fi
