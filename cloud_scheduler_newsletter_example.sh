#!/bin/bash

# Script to create a Cloud Scheduler job for the Life Tracker Daily Newsletter

# --- Configuration ---
# Project ID from user-provided CLOUD_SQL_CONNECTION_NAME
PROJECT_ID="your-gcp-project-id"

# Replace with your Cloud Run service URL for the ADK FastAPI service AFTER deployment
# This URL is typically in the format: https://[SERVICE_NAME]-[PROJECT_HASH]-[REGION].a.run.app
# Ensure this is the URL of the ADK FastAPI service.
APP_URL="https://<your-service-name>-<your-project-id>.<your-region>.run.app/newsletter/send-daily"

# Desired schedule for the newsletter (e.g., daily at 6 AM Europe/Berlin time)
# CRON Schedule Format: "MINUTE HOUR DAY_OF_MONTH MONTH DAY_OF_WEEK"
# Example: "0 6 * * *" for 6:00 AM daily
CRON_SCHEDULE="0 6 * * *"

# Cloud Scheduler Job Name
JOB_NAME="your-job-name"

# Region for the Cloud Scheduler job (from user-provided CLOUD_SQL_CONNECTION_NAME)
REGION="your-region"

# Timezone for the CRON schedule
# Example: "Europe/Berlin"
TIMEZONE="your-timezone"

# Description for the Cloud Scheduler job
JOB_DESCRIPTION="your-job-description"

# Internal API Key for invoking the Cloud Run service (recommended for security)
INTERNAL_API_KEY="your-internal-api-key"

# Service account email for invoking the Cloud Run service (recommended for security)
# This service account needs roles/run.invoker permission on the Cloud Run service.
# Replace [YOUR_SERVICE_ACCOUNT_EMAIL] with the actual service account email.
SERVICE_ACCOUNT_EMAIL="your-service-account-email"

# --- Validation ---
if [ "$PROJECT_ID" == "your-gcp-project-id" ]; then # Updated to actual value, so this check might be redundant or changed
  echo "Project ID is set to: $PROJECT_ID"
else
  echo "ERROR: PROJECT_ID is not set correctly. Expected 'your-gcp-project-id'."
  # exit 1 # Or remove this check if PROJECT_ID is hardcoded above
fi

if [ "$APP_URL" == "https://<your-service-name>-<your-project-id>.<your-region>.run.app/newsletter/send-daily" ]; then # Updated to actual value, so this check might be redundant or changed
  echo "ERROR: APP_URL is still a placeholder. Please edit the script."
  exit 1
fi

if [[ "$SERVICE_ACCOUNT_EMAIL" == "your-service-account-email" ]]; then
  echo "Warning: SERVICE_ACCOUNT_EMAIL is a placeholder. Please replace [YOUR_SERVICE_ACCOUNT_EMAIL] with an actual service account."
  echo "It's recommended to create a dedicated service account with roles/run.invoker permission."
  # Potentially exit 1 if a real SA is strictly required for the script to proceed
fi

# --- Summary ---

echo "--- Configuration Summary ---"
echo "Project ID: $PROJECT_ID"
echo "App URL Target: $APP_URL"
echo "Cron Schedule: $CRON_SCHEDULE (Timezone: $TIMEZONE)"
echo "Job Name: $JOB_NAME"
echo "Region: $REGION"
echo "Service Account for Invocation: $SERVICE_ACCOUNT_EMAIL"
echo "-----------------------------"
read -p "Proceed with creating/updating Cloud Scheduler job? (y/N): " confirmation
if [[ "$confirmation" != "y" ]] && [[ "$confirmation" != "Y" ]]; then
  echo "Operation cancelled by user."
  exit 0
fi

# --- Create/Update Cloud Scheduler Job ---
echo "Attempting to create/update Cloud Scheduler job '$JOB_NAME'..."

gcloud scheduler jobs create http "$JOB_NAME" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --schedule="$CRON_SCHEDULE" \
  --time-zone="$TIMEZONE" \
  --uri="$APP_URL" \
  --http-method=POST \
  --description="$JOB_DESCRIPTION" \
  --oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL" \
  --oidc-token-audience="$APP_URL" \
  --headers="X-Internal-API-Key=$INTERNAL_API_KEY" \
  --attempt-deadline="15m" \
  --max-retry-attempts=3 \
  --min-backoff="30s" \
  --max-backoff="300s" && \
echo "Cloud Scheduler job '$JOB_NAME' created/updated successfully." || \
echo "ERROR: Failed to create/update Cloud Scheduler job '$JOB_NAME'. Check gcloud logs and permissions."


echo ""
echo "--- Next Steps ---"
echo "To view the job: gcloud scheduler jobs describe $JOB_NAME --project=$PROJECT_ID --location=$REGION"
echo "To run the job manually (for testing): gcloud scheduler jobs run $JOB_NAME --project=$PROJECT_ID --location=$REGION"
echo "To view logs for the job executions, check Cloud Logging for Cloud Scheduler and your Cloud Run service."
echo "Ensure the service account '$SERVICE_ACCOUNT_EMAIL' has 'Cloud Run Invoker' role on the service '$APP_URL'."
