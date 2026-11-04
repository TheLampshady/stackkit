-include ../.env
export

SERVICE_DIR=../api_service
GCP_SERVICES_SRC=$(SERVICE_DIR)/gcp_services
GCP_SERVICES_DST=gcp_services

SERVICE_NAME ?= ${NAMESPACE}-agent
REGION ?= us-central1

.PHONY: build
build:
	uv export --frozen --package agents --no-dev --no-hashes --format requirements-txt > requirements.txt


# ------ SYNC ------
# Syncs entire gcp_services/ from service (source of truth).
# Only clients/gcp_services.py is excluded -- agents have their own
# Firestore-only override. Everything else syncs, even files agents
# don't import (fb_auth, gcp_storage, gcp_vertex) -- they're harmless.

.PHONY: sync-agents
sync-agents:
	@echo "Syncing gcp_services from $(GCP_SERVICES_SRC)/..."
	@if [ ! -d "$(GCP_SERVICES_SRC)" ]; then \
		echo "ERROR: Source directory missing: $(GCP_SERVICES_SRC)" >&2; \
		exit 1; \
	fi
	@rsync -a --exclude='clients/gcp_services.py' \
		$(GCP_SERVICES_SRC)/ $(GCP_SERVICES_DST)/
	@echo "Synced gcp_services/ (excluding clients/gcp_services.py)"

# ------ LOCAL DEV ------

.PHONY: adk-web
adk-web:
	cd agents && adk web --log_level DEBUG --reload_agents

.PHONY: adk-api
adk-api:
	cd agents && adk api_server --log_level DEBUG --reload_agents

# ------ DEPLOY ------

.PHONY: deploy-agent
deploy-agent: build
	uv run python deploy.py

.PHONY: deploy-agent-cr
deploy-agent-cr: build
	cd agents && adk deploy cloud_run \
		--project=${PROJECT_ID} \
		--region=${REGION} \
		--service_name=${SERVICE_NAME} \
		--app_name=${AGENT_NAME} \
		--with_ui \
		"."
