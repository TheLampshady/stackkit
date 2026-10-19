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

.PHONY: check-env
check-env:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is not set in .env" && exit 1)

.PHONY: deploy-gae
deploy-gae: check-env build
	@gcloud app deploy app.yaml --project=${PROJECT_ID} --version ${VERSION} --no-promote

## Ship the current code live. Run `make deploy` from the repo root so the
## frontend is built into static/ first.
.PHONY: deploy
deploy: check-env build
	@echo "Deploying $(SERVICE)..."
	@gcloud run deploy $(SERVICE) \
		--source=. \
		--project=$(PROJECT_ID) \
		--region=$(REGION) \
		--no-allow-unauthenticated \
		--iap \
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
