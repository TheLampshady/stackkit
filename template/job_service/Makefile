-include ../.env
export

REGION ?= us-central1
# Which job: a module in jobs/
JOB ?= example
# Cloud Run job names allow lowercase letters, digits and dashes
JOB_ID = $(subst _,-,$(if $(NAMESPACE),$(NAMESPACE)-,)$(JOB))
# When the timer runs it (cron, in TIME_ZONE): 6:00 every morning by default
SCHEDULE ?= 0 6 * * *
TIME_ZONE ?= Etc/UTC
# How long one run may take before it's stopped (up to 24h)
TASK_TIMEOUT ?= 60m

# ------ SYNC & BUILD ------

.PHONY: sync build
# Refresh this folder's copy of shared/gcp_services/. Projects made before
# shared/ existed have none, and keep their copies by hand.
sync:
	@if [ -f ../shared/sync.sh ]; then ../shared/sync.sh; fi

build: sync
	uv export --frozen --package job-service --no-dev --no-hashes --format requirements-txt > requirements.txt

# ------ RUN ------

## Run one job on this computer, against the emulator: make run JOB=example
.PHONY: run
run: sync
	uv run --project .. python main.py $(JOB)

# ------ DEPLOY ------

.PHONY: check-env
check-env:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is not set in .env" && exit 1)

## Put one job online (no Docker: Google builds it from this folder).
## It doesn't run until it's started by hand (make start) or by a timer (make schedule).
.PHONY: deploy
deploy: check-env build
	@gcloud run jobs deploy $(JOB_ID) \
		--source=. \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--tasks=1 \
		--max-retries=1 \
		--task-timeout=$(TASK_TIMEOUT) \
		--set-env-vars=JOB_NAME=$(JOB)$(if $(NAMESPACE),$(comma)NAMESPACE=$(NAMESPACE),) \
		--quiet

## Run the online job now, once
.PHONY: start
start: check-env
	@gcloud run jobs execute $(JOB_ID) --project=$(PROJECT_ID) --region=$(REGION)

## Run the online job on a timer (SCHEDULE, TIME_ZONE). Creates or updates it.
## Google's timer starts the job as the Compute Engine default account, which
## make -C gcp setup-iam lets do that.
.PHONY: schedule
schedule: check-env
	@number=$$(gcloud projects describe $(PROJECT_ID) --format='value(projectNumber)'); \
	action=create; \
	if gcloud scheduler jobs describe $(JOB_ID) --project=$(PROJECT_ID) --location=$(REGION) >/dev/null 2>&1; \
		then action=update; fi; \
	gcloud scheduler jobs $$action http $(JOB_ID) \
		--project=$(PROJECT_ID) \
		--location=$(REGION) \
		--schedule="$(SCHEDULE)" \
		--time-zone="$(TIME_ZONE)" \
		--uri="https://run.googleapis.com/v2/projects/$(PROJECT_ID)/locations/$(REGION)/jobs/$(JOB_ID):run" \
		--http-method=POST \
		--oauth-service-account-email="$$number-compute@developer.gserviceaccount.com" \
		--quiet

## List the job's recent runs, newest first
.PHONY: runs
runs: check-env
	@gcloud run jobs executions list --job=$(JOB_ID) --project=$(PROJECT_ID) --region=$(REGION)

comma := ,
