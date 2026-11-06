-include ../.env
export

SERVICE_NAME ?= ${NAMESPACE}-agent
REGION ?= us-central1

.PHONY: build
build:
	uv export --frozen --package agent_service --no-dev --no-hashes --format requirements-txt > requirements.txt


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
