-include .env
export

SERVICE_DIR=service

# Shared targets run every module's part; each optional module appends its own.
SETUP_TARGETS := setup-be
BUILD_TARGETS :=
LINT_TARGETS := lint-be
FORMAT_TARGETS := format-be
TYPECHECK_TARGETS := typecheck-be
TEST_TARGETS := test-be
CHECK_TARGETS := check-be

# stackkit:begin frontend
FE_DIR=frontend
SETUP_TARGETS += setup-fe
BUILD_TARGETS += build-fe
LINT_TARGETS += lint-fe
FORMAT_TARGETS += format-fe
TYPECHECK_TARGETS += typecheck-fe
TEST_TARGETS += test-fe
CHECK_TARGETS += check-fe
# stackkit:end frontend

# stackkit:begin agents
AGENTS_DIR=agent_service
TYPECHECK_TARGETS += typecheck-agents
TEST_TARGETS += test-agents
CHECK_TARGETS += check-agents
# stackkit:end agents

# ------ SETUP ------
.PHONY: setup setup-be
setup: $(SETUP_TARGETS)

setup-be:
	@uv sync --all-extras --all-groups
	@pre-commit install --config .config/.pre-commit-config.yaml
	@git config --local commit.template .config/.commit-message-template

# ------ RUN ------
.PHONY: run run-be
run:
ifdef FRONT_END_URL
	$(MAKE) run-be & $(MAKE) run-fe & wait
	@$(MAKE) run-be
else
	@$(MAKE) build
	@$(MAKE) run-be
endif

run-be:
	$(MAKE) -C ${SERVICE_DIR} run

.PHONY: emulator
emulator:
	$(MAKE) -C gcp emulator

# ------ BUILD & DEPLOY ------
.PHONY: build build-be
build: $(BUILD_TARGETS)

build-be:
	$(MAKE) -C ${SERVICE_DIR} build

.PHONY: deploy-app
deploy-app: build
	$(MAKE) -C ${SERVICE_DIR} deploy-gae

.PHONY: deploy-cr
deploy-cr: build
	$(MAKE) -C ${SERVICE_DIR} deploy

# ------- CODE QUALITY ------
.PHONY: lint lint-be format format-be typecheck typecheck-be test test-be check check-be
lint: $(LINT_TARGETS)

lint-be:
	uv run ruff check --fix .

format: $(FORMAT_TARGETS)

format-be:
	uv run ruff format .

typecheck: $(TYPECHECK_TARGETS)

typecheck-be:
	cd ${SERVICE_DIR} && uv run --all-groups ty check .

test: $(TEST_TARGETS)

test-be:
	cd ${SERVICE_DIR} && uv run --all-groups pytest tests

check: $(CHECK_TARGETS)

check-be: lint-be format-be typecheck-be test-be

.PHONY: hooks
hooks:
	@pre-commit run --all-files -c .config/.pre-commit-config.yaml

# stackkit:begin frontend
# ------ FRONTEND ------
.PHONY: setup-fe run-fe build-fe lint-fe format-fe typecheck-fe test-fe check-fe
setup-fe:
	@cd ${FE_DIR} && bun install

run-fe:
	cd ${FE_DIR} && bun dev

build-fe:
	@cd ${FE_DIR} && bun run build
	@rm -rf ${SERVICE_DIR}/static/
	@cp -r ${FE_DIR}/dist/ ${SERVICE_DIR}/static/

lint-fe:
	cd ${FE_DIR} && bun run lint

format-fe:
	cd ${FE_DIR} && bun run lint

typecheck-fe:
	cd ${FE_DIR} && bun run typecheck

test-fe:
	cd ${FE_DIR} && bun run test

check-fe: lint-fe format-fe typecheck-fe test-fe
# stackkit:end frontend

# stackkit:begin agents
# ------ AGENTS ------
.PHONY: deploy-agent deploy-agent-cr adk-web adk-api sync-agents typecheck-agents test-agents check-agents
deploy-agent:
	$(MAKE) -C $(AGENTS_DIR) deploy-agent

deploy-agent-cr:
	$(MAKE) -C $(AGENTS_DIR) deploy-agent-cr

adk-web:
	$(MAKE) -C $(AGENTS_DIR) adk-web

adk-api:
	$(MAKE) -C $(AGENTS_DIR) adk-api

sync-agents:
	$(MAKE) -C $(AGENTS_DIR) sync-agents

typecheck-agents:
	cd ${AGENTS_DIR} && uv run --all-groups ty check .

test-agents:
	cd ${AGENTS_DIR} && uv run --all-groups pytest tests

check-agents: typecheck-agents test-agents
# stackkit:end agents
