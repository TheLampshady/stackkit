-include ../.env
export

VERSION ?= main

# Static site on App Engine. Run `make deploy-app` from the repo root, which
# builds dist/ first. New versions don't take traffic until promoted.
.PHONY: deploy
deploy:
	@gcloud app deploy app.yaml --project=${PROJECT_ID} --version ${VERSION} --no-promote -q
