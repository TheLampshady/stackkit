-include .env
export

# Shared targets run every module's part; each optional module appends its own.
SETUP_TARGETS := setup-be
BUILD_TARGETS :=
LINT_TARGETS := lint-be
FORMAT_TARGETS := format-be
TYPECHECK_TARGETS :=
TEST_TARGETS :=
CHECK_TARGETS := lint-be format-be

# Without the API this is a static site: the frontend is the whole app
# stackkit:begin frontend
RUN_TARGET := run-fe
# stackkit:end frontend
# stackkit:begin gae
APP_DEPLOY := -C frontend deploy
# stackkit:end gae

# stackkit:begin api
SERVICE_DIR=api_service
TYPECHECK_TARGETS += typecheck-be
TEST_TARGETS += test-be
CHECK_TARGETS += typecheck-be test-be
RUN_TARGET := run-app
# stackkit:begin gae
APP_DEPLOY := -C ${SERVICE_DIR} deploy-gae
# stackkit:end gae
# The dev server sits beside the API and proxies /api to it
FE_PORT := 5173
# stackkit:end api

# stackkit:begin frontend
FE_DIR=frontend
FE_PORT ?= 8000
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

# stackkit:begin jobs
JOBS_DIR=job_service
# With no server or page, make run runs the example job
RUN_TARGET ?= run-job
TYPECHECK_TARGETS += typecheck-jobs
TEST_TARGETS += test-jobs
CHECK_TARGETS += check-jobs
# stackkit:end jobs

# stackkit:begin shared
# Every service deploys from its own folder with a copy of shared/gcp_services/.
# The targets that run, test, build or deploy a service refresh the copies first.
.PHONY: sync
sync:
	@shared/sync.sh

# stackkit:end shared
# ------ SETUP ------
.PHONY: setup setup-be
setup: $(SETUP_TARGETS)

setup-be:
	@uv sync --all-extras --all-groups
	@pre-commit install --config .config/.pre-commit-config.yaml
	@git config --local commit.template .config/.commit-message-template

# ------ RUN ------
.PHONY: run
run: $(RUN_TARGET)

# stackkit:begin api
.PHONY: run-app run-be
run-app:
# stackkit:begin frontend
ifdef FRONT_END_URL
	$(MAKE) run-be & $(MAKE) run-fe & wait
	@$(MAKE) run-be
else
# stackkit:end frontend
	@$(MAKE) build
	@$(MAKE) run-be
# stackkit:begin frontend
endif
# stackkit:end frontend

run-be: sync
	$(MAKE) -C ${SERVICE_DIR} run

# stackkit:end api

# stackkit:begin firebase
.PHONY: emulator
emulator:
	$(MAKE) -C gcp emulator
# stackkit:end firebase

# ------ BUILD & DEPLOY ------
.PHONY: build
build: $(BUILD_TARGETS)

# stackkit:begin api
.PHONY: build-be
build-be:
	$(MAKE) -C ${SERVICE_DIR} build

# stackkit:end api
# stackkit:begin gae
.PHONY: deploy-app
deploy-app: build
	$(MAKE) $(APP_DEPLOY)

# stackkit:end gae
# stackkit:begin cloud_run
.PHONY: deploy-cr
deploy-cr: build
	$(MAKE) -C ${SERVICE_DIR} deploy
# stackkit:end cloud_run

# ------- CODE QUALITY ------
.PHONY: lint lint-be format format-be typecheck test check
lint: $(LINT_TARGETS)

lint-be:
	uv run ruff check --fix .

format: $(FORMAT_TARGETS)

format-be:
	uv run ruff format .

typecheck: $(TYPECHECK_TARGETS)

test: $(TEST_TARGETS)

check: $(CHECK_TARGETS)

# stackkit:begin api
.PHONY: typecheck-be test-be
typecheck-be: sync
	cd ${SERVICE_DIR} && uv run --all-groups ty check .

test-be: sync
	cd ${SERVICE_DIR} && uv run --all-groups pytest tests

# stackkit:end api

.PHONY: hooks
hooks:
	@pre-commit run --all-files -c .config/.pre-commit-config.yaml

# stackkit:begin frontend
# ------ FRONTEND ------
.PHONY: setup-fe run-fe build-fe lint-fe format-fe typecheck-fe test-fe check-fe
setup-fe:
	@cd ${FE_DIR} && bun install

run-fe:
	cd ${FE_DIR} && bun dev --port $(FE_PORT)

build-fe:
	@cd ${FE_DIR} && bun run build
# stackkit:begin api
	@rm -rf ${SERVICE_DIR}/static/
	@cp -r ${FE_DIR}/dist/ ${SERVICE_DIR}/static/
# stackkit:end api

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
.PHONY: deploy-agent deploy-agent-cr adk-web adk-api typecheck-agents test-agents check-agents
deploy-agent:
	$(MAKE) -C $(AGENTS_DIR) deploy-agent

deploy-agent-cr:
	$(MAKE) -C $(AGENTS_DIR) deploy-agent-cr

adk-web:
	$(MAKE) -C $(AGENTS_DIR) adk-web

adk-api:
	$(MAKE) -C $(AGENTS_DIR) adk-api

typecheck-agents: sync
	cd ${AGENTS_DIR} && uv run --all-groups ty check .

test-agents: sync
	cd ${AGENTS_DIR} && uv run --all-groups pytest tests

check-agents: typecheck-agents test-agents
# stackkit:end agents

# stackkit:begin jobs
# ------ JOBS ------
# Background work that runs, finishes and exits: make run-job JOB=example
# Flags for job_service/cli.py go in ARGS: make start-job JOB=x ARGS="--payload db=zach"
.PHONY: run-job deploy-job start-job schedule-job unschedule-job list-jobs job-runs typecheck-jobs test-jobs check-jobs
run-job:
	$(MAKE) -C $(JOBS_DIR) run

deploy-job:
	$(MAKE) -C $(JOBS_DIR) deploy

start-job:
	$(MAKE) -C $(JOBS_DIR) start

schedule-job:
	$(MAKE) -C $(JOBS_DIR) schedule

unschedule-job:
	$(MAKE) -C $(JOBS_DIR) unschedule

list-jobs:
	$(MAKE) -C $(JOBS_DIR) list

job-runs:
	$(MAKE) -C $(JOBS_DIR) runs

typecheck-jobs: sync
	cd ${JOBS_DIR} && uv run --all-groups ty check .

test-jobs: sync
	cd ${JOBS_DIR} && uv run --all-groups pytest tests

check-jobs: typecheck-jobs test-jobs
# stackkit:end jobs
