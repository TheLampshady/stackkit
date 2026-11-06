.DEFAULT_GOAL := help
SAMPLES := $(shell mktemp -d -u)/stackkit-samples
# name:modules-to-remove. Covers every module kept and removed at least once.
SAMPLE_SPECS := \
	"all-modules:" \
	"team-tool:agents,jobs,notebooks,auth_firebase,storage,cloud_run,always_on" \
	"accounts-files:agents,jobs,notebooks,auth_iap,database,ai,frontend,gae" \
	"api-only:frontend,agents,jobs,notebooks,http_tests,auth_iap,auth_firebase,database,storage,ai,gae,always_on" \
	"jobs-only:api,frontend,agents,notebooks,http_tests,auth_iap,auth_firebase,storage,gae,cloud_run,always_on" \
	"static-site:api,agents,jobs,notebooks,http_tests,auth_firebase,database,storage,ai,cloud_run,always_on"

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Pinned to the template's ruff. Lint must pass without fixes: a fix that moves
# imports also moves the stackkit markers above them.
RUFF := uvx -q ruff@0.17.1

# The last stackkit before the server moved to api_service/ and shared/ was
# added. test-bootstrap builds a project with it, then adds to it with this one.
OLD_STACKKIT := a61a4a6

.PHONY: lint
lint: ## Check the scripts and template are ruff-clean as they stand
	$(RUFF) check skills template dev
	$(RUFF) format --check skills template dev

.PHONY: check-versions
check-versions: ## Compare the pinned Java/Node versions with what the latest Firebase CLI needs
	@uv run --python 3.13 --no-project dev/check_versions.py

.PHONY: test-bootstrap
test-bootstrap: lint check-versions ## Lint, bootstrap sample projects (convert one existing repo, grow one by adding parts), check for leftovers, run `make check` and `make build` in each
	@set -e; mkdir -p $(SAMPLES); for spec in $(SAMPLE_SPECS); do \
		name=$${spec%%:*}; remove=$${spec#*:}; dest=$(SAMPLES)/$$name; \
		echo "── $$name (remove: $${remove:-none})"; \
		uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py \
			--dest $$dest --name sample-$$name --display-name "Sample $$name" \
			--remove "$$remove" > $$dest-boot.json || { cat $$dest-boot.json; exit 1; }; \
		if grep -rq "stackkit" $$dest; then echo "stackkit traces left in $$dest"; exit 1; fi; \
		uv run --python 3.13 --no-project dev/check_docs.py $$dest || exit 1; \
		if grep -E '^ +"[^"]+:[0-9]+: ' $$dest-boot.json | grep -vE '^ +"[^"]+\.md:[0-9]+: '; then \
			echo "   leftover refs in code: wrap them in markers"; exit 1; fi; \
		uv run --python 3.13 --no-project skills/create/scripts/check.py --dest $$dest > $$dest.json \
			|| { cat $$dest.json; exit 1; }; echo "   ✓ make check, make build"; \
		python3 -c 'import json, sys; b, c = (json.load(open(f)) for f in sys.argv[1:]); \
			k, s = sorted(b["kept"]), sorted(c["status"]["parts"]); \
			sys.exit(0 if k == s else f"   status sees {s}, bootstrap kept {k}")' \
			$$dest-boot.json $$dest.json; echo "   ✓ status sees the kept parts"; \
		if [ -f $$dest/gcp/bin/setup_iam.sh ]; then bash -n $$dest/gcp/bin/setup_iam.sh \
			&& echo "   ✓ setup_iam.sh parses" || exit 1; fi; \
		for copy in $$dest/*_service/gcp_services; do [ -d $$copy ] || continue; \
			diff -rq -x __pycache__ $$dest/shared/gcp_services $$copy \
				|| { echo "   $$copy differs from shared/gcp_services"; exit 1; }; done; \
	done; \
	echo "── convert (an existing repo turned into a static site in place)"; \
	old=$(SAMPLES)/convert; mkdir -p $$old/images $$old/src; \
	echo '<h1>Menu</h1>' > $$old/index.html; echo img > $$old/images/a.png; \
	echo KEY=1 > $$old/images/.env; echo x > $$old/src/app.js; mkdir $$old/.git; \
	uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py --convert \
		--dest $$old --name sample-convert --display-name "Sample convert" \
		--remove api,agents,jobs,notebooks,http_tests,auth_firebase,database,storage,ai,cloud_run,always_on \
		--copy $$old/images=frontend/public/images > $$old-boot.json || { cat $$old-boot.json; exit 1; }; \
	test -d $$old/.git && test -f $$old/frontend/public/images/a.png \
		&& test ! -e $$old/frontend/public/images/.env && test ! -e $$old/src \
		&& test -f $$old-before-stackkit/index.html && test -f $$old-before-stackkit/src/app.js \
		|| { echo "   convert left the wrong layout"; exit 1; }; \
	uv run --python 3.13 --no-project skills/create/scripts/check.py --dest $$old > $$old.json \
		|| { cat $$old.json; exit 1; }; echo "   ✓ layout, make check, make build"; \
	echo "── add (an API-only project grows a web page, database and team sign-in)"; \
	grow=$(SAMPLES)/grow; fresh=$(SAMPLES)/grow-fresh; \
	uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py --dest $$grow \
		--name sample-grow --display-name "Sample grow" --env NAMESPACE=sample-grow \
		--remove frontend,agents,jobs,notebooks,http_tests,auth_iap,auth_firebase,database,storage,ai,gae,always_on \
		> $$grow-boot.json || { cat $$grow-boot.json; exit 1; }; \
	uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py --dest $$grow \
		--add frontend,database,auth_iap --display-name "Sample grow" > $$grow-add.json \
		|| { cat $$grow-add.json; exit 1; }; \
	uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py --dest $$fresh \
		--name sample-grow --display-name "Sample grow" --env NAMESPACE=sample-grow \
		--remove agents,jobs,notebooks,http_tests,auth_firebase,storage,ai,gae,always_on > /dev/null; \
	diff -rq $$grow $$fresh -x .env -x uv.lock || { echo "   adding differs from a fresh project"; exit 1; }; \
	uv run --python 3.13 --no-project skills/create/scripts/check.py --dest $$grow > $$grow.json \
		|| { cat $$grow.json; exit 1; }; echo "   ✓ same as a fresh project, make check, make build"; \
	echo "── add to an older project (made by stackkit $(OLD_STACKKIT): service/, no shared/)"; \
	legacy=$(SAMPLES)/legacy; old=$(SAMPLES)/stackkit-$(OLD_STACKKIT); mkdir -p $$old; \
	git archive $(OLD_STACKKIT) skills template | tar -x -C $$old; \
	uv run --python 3.13 --no-project $$old/skills/create/scripts/bootstrap.py --dest $$legacy \
		--name sample-legacy --display-name "Sample legacy" --env NAMESPACE=sample-legacy \
		--remove frontend,agents,notebooks,http_tests,auth_iap,auth_firebase,database,storage,ai,gae,always_on \
		> $$legacy-boot.json || { cat $$legacy-boot.json; exit 1; }; \
	uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py --dest $$legacy \
		--add database > $$legacy-add.json || { cat $$legacy-add.json; exit 1; }; \
	test ! -e $$legacy/api_service && test ! -e $$legacy/shared && test -f $$legacy/service/app.py \
		&& ! grep -q firestore_db $$legacy/service/app_settings.py \
		&& grep -q '"path": "service/app_settings.py"' $$legacy-add.json \
		&& grep -q 'firestore_db_name' $$legacy-add.json \
		&& test "$$(grep -c '"reason"' $$legacy-add.json)" = 1 \
		|| { echo "   adding to an older project changed its layout, or didn't report its settings"; cat $$legacy-add.json; exit 1; }; \
	sed -i '/^    namespace: str | None = /a\    firestore_db_name: str | None = os.environ.get("FIRESTORE_DB_NAME") or namespace\n    use_emulator: bool = env_var_as_bool("USE_EMULATOR", not IS_GCP)' $$legacy/service/app_settings.py; \
	uv run --python 3.13 --no-project skills/create/scripts/check.py --dest $$legacy > $$legacy.json \
		|| { cat $$legacy.json; exit 1; }; echo "   ✓ kept its layout, reported its settings, make check, make build"; \
	rm -rf $(SAMPLES)

.PHONY: claude
claude: ## Reinstall this repo as a Claude plugin (local scope) — safe to re-run
	@claude plugin uninstall stackkit >/dev/null 2>&1 || true
	@claude plugin marketplace add $(PWD) >/dev/null
	@claude plugin marketplace update stackkit-marketplace >/dev/null
	claude plugin install stackkit@stackkit-marketplace
