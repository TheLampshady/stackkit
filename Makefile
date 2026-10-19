.DEFAULT_GOAL := help
SAMPLES := $(shell mktemp -d -u)/stackkit-samples
# name:modules-to-remove. Covers every module kept and removed at least once.
SAMPLE_SPECS := \
	"all-modules:" \
	"team-tool:agents,notebooks,auth_firebase,storage,cloud_run,always_on" \
	"accounts-files:agents,notebooks,auth_iap,database,ai,frontend,gae" \
	"api-only:frontend,agents,notebooks,http_tests,auth_iap,auth_firebase,database,storage,ai,gae,always_on" \
	"static-site:api,agents,notebooks,http_tests,auth_firebase,database,storage,ai,cloud_run,always_on"

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Pinned to the template's ruff. Lint must pass without fixes: a fix that moves
# imports also moves the stackkit markers above them.
RUFF := uvx -q ruff@0.17.1

.PHONY: lint
lint: ## Check the scripts and template are ruff-clean as they stand
	$(RUFF) check skills template
	$(RUFF) format --check skills template

.PHONY: test-bootstrap
test-bootstrap: lint ## Lint, bootstrap sample projects, check for leftovers, run `make check` in each
	@set -e; mkdir -p $(SAMPLES); for spec in $(SAMPLE_SPECS); do \
		name=$${spec%%:*}; remove=$${spec#*:}; dest=$(SAMPLES)/$$name; \
		echo "── $$name (remove: $${remove:-none})"; \
		uv run --python 3.13 --no-project skills/create/scripts/bootstrap.py \
			--dest $$dest --name sample-$$name --display-name "Sample $$name" \
			--remove "$$remove" > $$dest-boot.json || { cat $$dest-boot.json; exit 1; }; \
		if grep -rq "stackkit" $$dest; then echo "stackkit traces left in $$dest"; exit 1; fi; \
		if grep -E '^ +"[^"]+:[0-9]+: ' $$dest-boot.json | grep -vE '^ +"[^"]+\.md:[0-9]+: '; then \
			echo "   leftover refs in code: wrap them in markers"; exit 1; fi; \
		uv run --python 3.13 --no-project skills/create/scripts/check.py --dest $$dest > $$dest.json \
			|| { cat $$dest.json; exit 1; }; echo "   ✓ make check"; \
	done; rm -rf $(SAMPLES)

.PHONY: claude
claude: ## Reinstall this repo as a Claude plugin (local scope) — safe to re-run
	@claude plugin uninstall stackkit >/dev/null 2>&1 || true
	@claude plugin marketplace add $(PWD) >/dev/null
	@claude plugin marketplace update stackkit-marketplace >/dev/null
	claude plugin install stackkit@stackkit-marketplace
