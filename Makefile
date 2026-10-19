.DEFAULT_GOAL := help
SAMPLES := $(shell mktemp -d -u)/stackkit-samples

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: test-bootstrap
test-bootstrap: ## Bootstrap sample projects and run `make check` in each
	@set -e; for spec in "all-modules:" "no-agents:agents,notebooks,http_tests" "no-frontend:frontend,notebooks,http_tests"; do \
		name=$${spec%%:*}; remove=$${spec#*:}; dest=$(SAMPLES)/$$name; \
		echo "── $$name (remove: $${remove:-none})"; \
		uv run --python 3.13 --no-project skills/bootstrap/scripts/bootstrap.py \
			--dest $$dest --name sample-$$name --display-name "Sample $$name" \
			--remove "$$remove" --env USE_EMULATOR=true > /dev/null; \
		if grep -rq "stackkit" $$dest; then echo "stackkit traces left in $$dest"; exit 1; fi; \
		cd $$dest && git init -q && uv lock -q && uv sync -q --all-extras --all-groups; \
		if [ -d frontend ]; then (cd frontend && bun install > /dev/null 2>&1); fi; \
		$(MAKE) --no-print-directory check > /dev/null && echo "   ✓ make check"; cd - > /dev/null; \
	done; rm -rf $(SAMPLES)

.PHONY: claude
claude: ## Reinstall this repo as a Claude plugin (local scope) — safe to re-run
	@claude plugin uninstall stackkit >/dev/null 2>&1 || true
	@claude plugin marketplace add $(PWD) >/dev/null
	@claude plugin marketplace update stackkit-marketplace >/dev/null
	claude plugin install stackkit@stackkit-marketplace
