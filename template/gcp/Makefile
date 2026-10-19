-include ../.env
export

FIRESTORE_DATA="./firestore_data"

# ------ CLI ------
# stackkit:begin gae
# Usage: make cli ARGS="split-cookie https://your-app.appspot.com/ -n 5000"
# stackkit:end gae
.PHONY: cli
cli:
	@uv run --project . cli.py $(ARGS)

# stackkit:begin gae
dispatch:
	gcloud app deploy dispatch.yaml --project ${PROJECT_ID}
# stackkit:end gae

# stackkit:begin storage
# Bucket name matches service settings: FIRESTORE_BUCKET_NAME, else {PROJECT_ID}-{NAMESPACE}
cors:
	gcloud storage buckets update gs://$(or ${FIRESTORE_BUCKET_NAME},${PROJECT_ID}-${NAMESPACE}) --cors-file=cors.json --project=${PROJECT_ID}
# stackkit:end storage

# stackkit:begin gae
setup-iam:
	@bin/setup_iam.sh
# stackkit:end gae

# stackkit:begin firebase
# ------ FIREBASE EMULATOR ------

# stackkit:begin database
sync-db:
	@bin/sync_db.sh "${PROJECT_ID}" "${FIRESTORE_DATA}"

# stackkit:end database
.PHONY: emulator
emulator:
	@bin/emulator.sh --data "${FIRESTORE_DATA}"

.PHONY: emulator-empty
emulator-empty:
	@bin/emulator.sh --empty

# Create the project's cloud resources named in .env (skips the ones that
# exist, asks once before creating the rest), then deploy the database rules
# and indexes. Safe to rerun.
.PHONY: provision
provision:
	@uv run --project . cli.py provision
# stackkit:begin database
	@$(MAKE) --no-print-directory rules
	@printf "Deploy Firestore indexes to $(DB_NAME) in $(PROJECT_ID)? [y/N] "; read answer; \
	case "$$answer" in [yY]*) $(MAKE) --no-print-directory indexes ;; *) echo "Indexes skipped." ;; esac
# stackkit:end database
# stackkit:end firebase


# stackkit:begin database
# ------ FIRESTORE RULES & INDEXES ------

# The Firebase CLI deploys to the database written literally in firebase.json;
# it cannot read .env. check-db fails fast if that name drifts from the
# database the service uses (FIRESTORE_DB_NAME, else NAMESPACE, else (default)).
DEFAULT_DB := (default)
DB_NAME = $(or $(FIRESTORE_DB_NAME),$(NAMESPACE),$(DEFAULT_DB))

.PHONY: check-db
check-db:
	@db=$$(python3 -c 'import json; f = json.load(open("firebase.json"))["firestore"]; f = f[0] if isinstance(f, list) else f; print(f.get("database", "(default)"))'); \
	if [ "$$db" != "$(DB_NAME)" ]; then \
		echo "firebase.json names database '$$db' but .env resolves the service database to '$(DB_NAME)'."; \
		echo "Rules and indexes would deploy to the wrong database. Edit gcp/firebase.json or NAMESPACE / FIRESTORE_DB_NAME in .env."; \
		exit 1; \
	fi

rules: check-db
	firebase deploy -P ${PROJECT_ID} --only firestore:rules

indexes: check-db
	firebase deploy -P ${PROJECT_ID} --only firestore:indexes

indexes-save: check-db
	firebase -P ${PROJECT_ID} firestore:indexes --database $(DB_NAME) > firestore.indexes.json
# stackkit:end database
