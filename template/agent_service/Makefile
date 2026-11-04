-include ../.env
export

SERVICE_NAME ?= ${NAMESPACE}-agent
REGION ?= us-central1

.PHONY: build
build: sync
	uv export --frozen --package agents --no-dev --no-hashes --format requirements-txt > requirements.txt


# ------ SYNC ------
# Refresh this folder's copy of shared/gcp_services/ (the one to edit). Projects
# made before shared/ existed have none, and keep their copies by hand.

.PHONY: sync
sync:
	@if [ -f ../shared/sync.sh ]; then ../shared/sync.sh; fi

# ------ LOCAL DEV ------

.PHONY: adk-web
adk-web: sync
	cd agents && adk web --log_level DEBUG --reload_agents

.PHONY: adk-api
adk-api: sync
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
