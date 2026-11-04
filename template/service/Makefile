-include ../.env
export

REGION ?= us-central1

# ------ BUILD ------

.PHONY: build
build:
	uv export --frozen --package service --no-dev --no-hashes --format requirements-txt > requirements.txt

# ------ RUN ------

.PHONY: run
run:
	uv run --project .. uvicorn app:app --host 0.0.0.0 --port 8000 --reload


# ------ DEPLOY ------

VERSION ?= main
SERVICE = $(or $(NAMESPACE),$(VERSION))

# stackkit:begin cloud_run
# Who can reach the Cloud Run service: anyone, unless IAP guards it
ACCESS_FLAGS := --allow-unauthenticated
# stackkit:begin auth_iap
ACCESS_FLAGS := --no-allow-unauthenticated --iap
# stackkit:end auth_iap
# Scale to zero when idle: free, but the first visit after a quiet spell waits.
# --cpu-boost below shortens that wait; it's billed only while an instance starts.
# MAX_INSTANCES caps how many run at once, so a traffic spike can't run up the
# bill (Cloud Run's own default is 100).
# stackkit:begin gae
# Keep it in step with max_instances in service/app.yaml.
# stackkit:end gae
MIN_INSTANCES := 0
# stackkit:begin always_on
MIN_INSTANCES := 1
# stackkit:end always_on
MAX_INSTANCES := 2
SCALE_FLAGS := --min-instances=$(MIN_INSTANCES) --max-instances=$(MAX_INSTANCES)
# stackkit:end cloud_run

.PHONY: check-env
check-env:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is not set in .env" && exit 1)

# stackkit:begin gae
.PHONY: deploy-gae
deploy-gae: check-env build
	@gcloud app deploy app.yaml --project=${PROJECT_ID} --version ${VERSION} --no-promote

# stackkit:end gae
# stackkit:begin cloud_run
## Ship the current code live. Run `make deploy-cr` from the repo root so the
## frontend is built into static/ first.
.PHONY: deploy
deploy: check-env build
	@echo "Deploying $(SERVICE)..."
	@gcloud run deploy $(SERVICE) \
		--source=. \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		$(ACCESS_FLAGS) \
		$(SCALE_FLAGS) \
		--cpu-boost \
		$(if $(NAMESPACE),--set-env-vars=NAMESPACE=$(NAMESPACE),) \
		--quiet
	@echo ""
	@echo "Live: $$(gcloud run services describe $(SERVICE) --project=$(PROJECT_ID) --region=$(REGION) --format='value(status.url)')"

## List past deploys, newest first.
.PHONY: deploys
deploys: check-env
	@gcloud run revisions list \
		--service=$(SERVICE) \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--sort-by=~metadata.creationTimestamp \
		--format='table(metadata.name,metadata.creationTimestamp,status.conditions[0].status:label=READY)'
# stackkit:end cloud_run
