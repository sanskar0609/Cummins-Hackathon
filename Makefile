# ══════════════════════════════════════════════════════════════════════════════
#  Supply Chain Intelligence OS — Makefile
#  Usage: make <target>
#  Requires: Docker Desktop, docker compose v2
# ══════════════════════════════════════════════════════════════════════════════

.DEFAULT_GOAL := help
COMPOSE        := docker compose
ENV_FILE       := .env

.PHONY: help up down logs ps clean infra validate copy-env

help: ## Show this help message
	@echo ""
	@echo "  Supply Chain Intelligence OS — Available commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""

copy-env: ## Copy .env.example to .env (only if .env does not exist)
	@if not exist $(ENV_FILE) ( \
		copy .env.example .env && echo .env created from .env.example \
	) else ( \
		echo .env already exists — skipping \
	)

validate: ## Validate docker-compose config syntax
	$(COMPOSE) config

up: ## Start all infrastructure services in detached mode
	$(COMPOSE) up -d

down: ## Stop and remove all containers (volumes preserved)
	$(COMPOSE) down

logs: ## Tail logs for all running services
	$(COMPOSE) logs -f

ps: ## Show status of all containers
	$(COMPOSE) ps

infra: ## Start infra-only services (postgres, redis, kafka, neo4j, mlflow)
	$(COMPOSE) up -d postgres redis zookeeper kafka neo4j mlflow

clean: ## Stop all containers AND remove volumes (destructive — data will be lost)
	@echo "WARNING: This will delete all container volumes and data."
	$(COMPOSE) down --volumes --remove-orphans
