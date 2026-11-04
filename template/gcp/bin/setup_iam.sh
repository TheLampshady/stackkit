#!/bin/bash

# ----------------------------------------- #
# Grants the server's Google service accounts the roles they need.
# Run once per Google Cloud project, and again after adding a secret, by
# someone who can change the project's permissions (Owner, or Project IAM Admin).
#
# Reads PROJECT_ID from the root .env file.
#
# Newer projects no longer give default service accounts the Editor role, so
# every role is granted explicitly. Roles granted to the runtime account(s):
#   - secretmanager.secretAccessor (per secret)
# stackkit:begin database
#   - datastore.user (Firestore)
# stackkit:end database
# stackkit:begin storage
#   - storage.objectUser (the file bucket)
#   - iam.serviceAccountTokenCreator (for GCS signed URLs)
# stackkit:end storage
# stackkit:begin auth_firebase
#   - firebaseauth.viewer (look up signed-in users)
# stackkit:end auth_firebase
# stackkit:begin ai
#   - aiplatform.user (Gemini and Claude on Vertex AI)
# stackkit:end ai
# stackkit:begin agents
# Agents deploy on their own: on Cloud Run as the Compute Engine default
# account (datastore.user, aiplatform.user), on Agent Engine as its Reasoning
# Engine service agent (datastore.user; its own role covers Vertex AI).
# stackkit:end agents
# stackkit:begin cloud_run,agents
# And the Compute Engine default account, which builds Cloud Run source
# deploys, gets run.builder (without it, deploying fails with a permission error).
# stackkit:end cloud_run,agents
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

# stackkit:begin cloud_run,agents
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
COMPUTE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
# stackkit:end cloud_run,agents
RUNTIME_ACCOUNTS=()
# stackkit:begin gae
RUNTIME_ACCOUNTS+=("${PROJECT_ID}@appspot.gserviceaccount.com")
# stackkit:end gae
# stackkit:begin cloud_run
RUNTIME_ACCOUNTS+=("$COMPUTE_ACCOUNT")
# stackkit:end cloud_run

grant_project_role() {
  echo "Granting $2 to $1..."
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$1" \
    --role="$2" \
    --condition=None \
    --quiet > /dev/null
}

echo "Project:  $PROJECT_ID"
echo "Accounts: ${RUNTIME_ACCOUNTS[*]}"
echo ""

# --- Secret Manager access ---
# Same names as SECRET_KEY_NAMES in service/app_settings.py
SECRETS=()

if [[ ${#SECRETS[@]} -eq 0 ]]; then
  echo "No secrets listed in SECRETS; skipping Secret Manager access."
fi

for ACCOUNT in "${RUNTIME_ACCOUNTS[@]}"; do
  # The ${...+...} form keeps an empty array safe under `set -u` on bash 3.2 (macOS)
  for SECRET in ${SECRETS[@]+"${SECRETS[@]}"}; do
    echo "Granting secretmanager.secretAccessor on $SECRET to $ACCOUNT..."
    gcloud secrets add-iam-policy-binding "$SECRET" \
      --member="serviceAccount:$ACCOUNT" \
      --role="roles/secretmanager.secretAccessor" \
      --project="$PROJECT_ID" \
      --quiet > /dev/null
  done
  # stackkit:begin database
  grant_project_role "$ACCOUNT" roles/datastore.user
  # stackkit:end database
  # stackkit:begin storage
  grant_project_role "$ACCOUNT" roles/storage.objectUser
  # --- IAM signBlob for GCS signed URLs ---
  echo "Granting iam.serviceAccountTokenCreator on $ACCOUNT to itself..."
  gcloud iam service-accounts add-iam-policy-binding "$ACCOUNT" \
    --member="serviceAccount:$ACCOUNT" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project="$PROJECT_ID" \
    --quiet > /dev/null
  # stackkit:end storage
  # stackkit:begin auth_firebase
  grant_project_role "$ACCOUNT" roles/firebaseauth.viewer
  # stackkit:end auth_firebase
  # stackkit:begin ai
  grant_project_role "$ACCOUNT" roles/aiplatform.user
  # stackkit:end ai
done

# stackkit:begin agents
# --- Agents: Cloud Run (make deploy-agent-cr) and Agent Engine (make deploy-agent) ---
grant_project_role "$COMPUTE_ACCOUNT" roles/datastore.user
grant_project_role "$COMPUTE_ACCOUNT" roles/aiplatform.user
# Google creates this service agent on the first Agent Engine deploy
AGENT_ENGINE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
grant_project_role "$AGENT_ENGINE_ACCOUNT" roles/datastore.user \
  || echo "Skipped $AGENT_ENGINE_ACCOUNT: run make deploy-agent once, then rerun this script."
# stackkit:end agents

# stackkit:begin cloud_run,agents
# --- Cloud Run source deploys build as the Compute Engine default account ---
grant_project_role "$COMPUTE_ACCOUNT" roles/run.builder
echo "(New roles take a couple of minutes to apply before the first deploy.)"
# stackkit:end cloud_run,agents

echo ""
echo "Done. All IAM roles granted."
