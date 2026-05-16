SHELL := /bin/bash

ROOT_COMPOSE := docker-compose.yml
BOTS_COMPOSE := Bots/docker-compose.yml
DOCKER_COMPOSE := docker compose

.PHONY: up down logs bots-up bots-down app-up app-down wait-bots

up: bots-up wait-bots app-up

bots-up:
	@$(DOCKER_COMPOSE) -f $(BOTS_COMPOSE) up -d --build

wait-bots:
	@echo "Waiting for Bots MCP container to be running..."
	@for _ in $$(seq 1 60); do \
		container_id="$$( $(DOCKER_COMPOSE) -f $(BOTS_COMPOSE) ps -q mcp 2>/dev/null )"; \
		if [[ -n "$$container_id" ]] && [[ "$$(docker inspect -f '{{.State.Running}}' "$$container_id" 2>/dev/null)" == "true" ]]; then \
			echo "Bots MCP is ready"; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "Bots MCP did not become ready in time" >&2; \
	exit 1

app-up:
	@$(DOCKER_COMPOSE) -f $(ROOT_COMPOSE) up --build

down: app-down bots-down

app-down:
	@$(DOCKER_COMPOSE) -f $(ROOT_COMPOSE) down

bots-down:
	@$(DOCKER_COMPOSE) -f $(BOTS_COMPOSE) stop

logs:
	@$(DOCKER_COMPOSE) -f $(ROOT_COMPOSE) logs -f app & \
	$(DOCKER_COMPOSE) -f $(BOTS_COMPOSE) logs -f api mcpdo