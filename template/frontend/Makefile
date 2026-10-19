-include ../.env
export

VERSION ?= main

# Multi-page static site (app.yaml)
.PHONY: deploy
deploy:
	@gcloud app deploy app.yaml --project=${PROJECT_ID} --version ${VERSION} --no-promote -q

# Single-page app (app-spa.yaml)
.PHONY: deploy-spa
deploy-spa:
	@gcloud app deploy app-spa.yaml --project=${PROJECT_ID} --version ${VERSION} --no-promote -q
