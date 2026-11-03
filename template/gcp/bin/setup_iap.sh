#!/bin/bash

# ----------------------------------------- #
# First-time setup for Identity-Aware Proxy (IAP).
# Run by whoever looks after the Google Cloud project.
#
# Reads PROJECT_ID and NAMESPACE from the root .env file.
#
# One custom OAuth client serves every IAP site in the project. Its ID and
# secret are kept in Secret Manager under the fixed names below.
#
#   setup_iap.sh prepare              Enable IAP, let it reach the service
#   setup_iap.sh client               Save the OAuth client ID and secret
#   setup_iap.sh apply                Point the whole project's IAP at that client
#   setup_iap.sh grant MEMBER [project|service]
#                                     Let a person or group in
#
# MEMBER looks like group:team@example.com or user:client@example.com.
# ----------------------------------------- #

set -euo pipefail

CLIENT_ID_SECRET="IAP_OAUTH_CLIENT_ID"
CLIENT_SECRET_SECRET="IAP_OAUTH_CLIENT_SECRET"
ROLE="roles/iap.httpsResourceAccessor"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(cd "$SCRIPT_DIR/../.." && pwd)/.env"

env_value() {
  grep -E "^$1=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '[:space:]' || true
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

PROJECT_ID=$(env_value PROJECT_ID)
NAMESPACE=$(env_value NAMESPACE)
REGION="${REGION:-us-central1}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: PROJECT_ID not set in $ENV_FILE"
  exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

# Saves a value as a new version of a secret, creating the secret if needed.
save_secret() {
  local name="$1" value="$2"
  if ! gcloud secrets describe "$name" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$name" --replication-policy=automatic --project="$PROJECT_ID" --quiet
  fi
  printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- --project="$PROJECT_ID" --quiet
}

read_secret() {
  gcloud secrets versions access latest --secret="$1" --project="$PROJECT_ID"
}

prepare() {
  echo "Enabling IAP in $PROJECT_ID..."
  gcloud services enable iap.googleapis.com secretmanager.googleapis.com --project="$PROJECT_ID"
  # stackkit:begin cloud_run
  # IAP calls Cloud Run as its own service agent, which needs permission to invoke it.
  gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
    --role="roles/run.invoker" --condition=None --quiet >/dev/null
  # stackkit:end cloud_run
  # stackkit:begin gae
  # App Engine needs IAP switched on for the app once, after its first deploy.
  gcloud iap web enable --resource-type=app-engine --project="$PROJECT_ID" || \
    echo "App Engine has no app yet. Deploy once, then run this again."
  # stackkit:end gae
  cat <<EOF

Next, in the Google Cloud console (this part has no command):

  1. Google Auth Platform > Branding: set the app name and support email.
  2. Google Auth Platform > Audience: choose External if anyone outside your
     company (clients, say) needs in, otherwise Internal.
  3. Google Auth Platform > Clients > Create client > Web application.
     Name it "IAP". Copy the client ID, then add this authorized redirect URI
     (replace CLIENT_ID) and save:
       https://iap.googleapis.com/v1/oauth/clientIds/CLIENT_ID:handleRedirect

Then run: make iap-client
EOF
}

client() {
  local id secret
  read -r -p "OAuth client ID: " id
  read -r -s -p "OAuth client secret (hidden): " secret
  echo
  if [[ -z "$id" || -z "$secret" ]]; then
    echo "Error: both the client ID and the secret are needed."
    exit 1
  fi
  save_secret "$CLIENT_ID_SECRET" "$id"
  save_secret "$CLIENT_SECRET_SECRET" "$secret"
  echo "Saved to Secret Manager as $CLIENT_ID_SECRET and $CLIENT_SECRET_SECRET."
  echo "Then run: make iap-apply"
}

apply() {
  local file
  file="$(mktemp)"
  trap 'rm -f "$file"' EXIT
  chmod 600 "$file"
  cat > "$file" <<EOF
accessSettings:
  oauthSettings:
    clientId: $(read_secret "$CLIENT_ID_SECRET")
    clientSecret: $(read_secret "$CLIENT_SECRET_SECRET")
EOF
  gcloud iap settings set "$file" --project="$PROJECT_ID"
  echo "Every IAP site in $PROJECT_ID now uses this client."
  echo "Then give people access: make iap-grant MEMBER=group:team@example.com"
}

grant() {
  local member="${1:-}" scope="${2:-service}"
  if [[ -z "$member" ]]; then
    echo "Usage: make iap-grant MEMBER=group:team@example.com [SCOPE=project|service]"
    exit 1
  fi
  if [[ "$scope" == "project" ]]; then
    # Everyone granted here reaches every IAP site in the project.
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="$member" --role="$ROLE" --condition=None --quiet >/dev/null
    echo "$member can reach every IAP site in $PROJECT_ID."
    return
  fi
  # Granted on one site, so one client's people can't open another's.
  # stackkit:begin cloud_run
  gcloud iap web add-iam-policy-binding \
    --resource-type=cloud-run --service="${NAMESPACE:-main}" --region="$REGION" \
    --member="$member" --role="$ROLE" --project="$PROJECT_ID" --condition=None --quiet >/dev/null
  # stackkit:end cloud_run
  # stackkit:begin gae
  gcloud iap web add-iam-policy-binding \
    --resource-type=app-engine \
    --member="$member" --role="$ROLE" --project="$PROJECT_ID" --condition=None --quiet >/dev/null
  # stackkit:end gae
  echo "$member can reach ${NAMESPACE:-this site}."
}

case "${1:-}" in
  prepare) prepare ;;
  client) client ;;
  apply) apply ;;
  grant) shift; grant "$@" ;;
  *) sed -n '3,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
