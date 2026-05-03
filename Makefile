# zefflow developer convenience targets.
.PHONY: help hooks repo-map-check repo-map-refresh repo-map-rebuild

help:
	@awk 'BEGIN{FS=":.*##"; printf "Targets:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

hooks: ## Install git hooks (pre-commit staleness detector).
	@bash scripts/install-hooks.sh

repo-map-check: ## Run the Tier-1 staleness detector now (no LLM).
	@bash scripts/check-repo-map.sh

repo-map-refresh: ## Tier-2: ask the agent to update only the affected docs.
	@cd agent-workflows && uv run agent-refresh refresh

repo-map-rebuild: ## Tier-3: full re-run of the repo-explainer methodology.
	@echo "[repo-map] Tier-3 rebuild is not yet wired (agent-driven full rebuild)."
	@echo "          For now: follow notes/repo_overwiew.md from Phase 0 manually,"
	@echo "          then 'agent-refresh status' to verify."
