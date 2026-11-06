-include ../.env
export

# Which job: a module in jobs/
JOB ?= example

# ------ SYNC & BUILD ------

.PHONY: sync build
# Refresh this folder's copy of shared/gcp_services/. Projects made before
# shared/ existed have none, and keep their copies by hand.
sync:
	@if [ -f ../shared/sync.sh ]; then ../shared/sync.sh; fi

build: sync
	uv export --frozen --package job_service --no-dev --no-hashes --format requirements-txt > requirements.txt

# ------ RUN, DEPLOY, SCHEDULE ------
# These call cli.py, which does the work (see Readme.md). Pass its flags in ARGS:
#   make start-job JOB=nightly ARGS="--payload db=zach --wait"

CLI = uv run --package job_service --group cli python cli.py
# ALL=1 means every job instead of JOB
TARGET = $(if $(ALL),--all,$(JOB))

## Run one job on this computer, against the emulator: make run JOB=example
.PHONY: run
run: sync
	$(CLI) run $(JOB) --local $(ARGS)

## Put jobs online (no Docker: Google builds the folder). They don't run yet.
.PHONY: deploy
deploy:
	$(CLI) deploy $(TARGET) $(if $(TASK_TIMEOUT),--timeout $(TASK_TIMEOUT)) $(ARGS)

## Run the online job now, once
.PHONY: start
start:
	$(CLI) run $(JOB) --remote $(ARGS)

## Put a job on a timer. With SCHEDULE it sets one timer from SCHEDULE and
## TIME_ZONE; without, it sets the ones in job_service.toml (ALL=1: every job's).
.PHONY: schedule
schedule:
	$(CLI) schedule $(TARGET) $(if $(SCHEDULE),--cron "$(SCHEDULE)") $(if $(TIME_ZONE),--tz $(TIME_ZONE)) $(ARGS)

## Take a job off its timer
.PHONY: unschedule
unschedule:
	$(CLI) unschedule $(JOB) $(ARGS)

## What's online and on a timer
.PHONY: list
list:
	$(CLI) list $(ARGS)

## Recent runs, newest first (ALL=1 for every job; ARGS="--active" for ones in progress)
.PHONY: runs
runs:
	$(CLI) runs $(if $(ALL),,$(JOB)) $(ARGS)

## Any cli.py command: make cli ARGS="deploy --all"
.PHONY: cli
cli:
	$(CLI) $(ARGS)

