#!/bin/bash

# ----------------------------------------- #
# Grants required IAM roles to the App Engine
# default service account.
#
# Reads PROJECT_ID from the root .env file.
#
# Roles granted:
#   - secretmanager.secretAccessor (per secret)
#   - iam.serviceAccountTokenCreator (for GCS signed URLs)
# ----------------------------------------- #

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

PROJECT_ID=$(grep -E '^PROJECT_ID=' "$ENV_FILE" | cut -d'=' -f2 | tr -d '[:space:]')

if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: PROJECT_ID not set in $ENV_FILE"
  exit 1
fi

SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

echo "Project:         $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"
echo ""

# --- Secret Manager access ---
SECRETS=(
  "MAPS_API_KEY"
  "GOOGLE_PHOTOS_CLIENT_ID"
  "GOOGLE_PHOTOS_CLIENT_SECRET"
)

for SECRET in "${SECRETS[@]}"; do
  echo "Granting secretmanager.secretAccessor on $SECRET..."
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" \
    --quiet
done

# --- IAM signBlob for GCS signed URLs ---
echo ""
echo "Granting iam.serviceAccountTokenCreator on $SERVICE_ACCOUNT..."
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="$PROJECT_ID" \
  --quiet

echo ""
echo "Done. All IAM roles granted."
