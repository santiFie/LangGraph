.PHONY: up down build logs build-openalex

PROJECT_ROOT := $(shell pwd)
COMPOSE := docker compose -f "$(PROJECT_ROOT)/docker-compose.yml"
BOTS_COMPOSE := docker compose -f "/home/santi/Documentos/Prebi/bots-detector/docker-compose.yml"

# ─── Levantar todo ────────────────────────────────────────────────────────────
up:
	@echo "▶  Starting external services (Bots Detector)..."
	$(BOTS_COMPOSE) up -d
	@echo "▶  Starting MCPs (DSpace + MinIO)..."
	$(COMPOSE) up -d
	@echo "▶  Iniciando LangGraph Platform local..."
	LANGGRAPH_STARTUP_TIMEOUT=30 langgraph dev --allow-blocking

# ─── Build images ─────────────────────────────────────────────────────────────
# NOTE: OpenAlex MCP uses stdio transport → not in docker-compose, built standalone.
build:
	@echo "▶  Building MCP images..."
	$(BOTS_COMPOSE) build
	$(COMPOSE) build
	@echo "▶  Building OpenAlex MCP image (stdio, on-demand)..."
	docker build -t multi-servicesproject-openalex-mcp "$(PROJECT_ROOT)/MCPs/OpenAlex MCP"

# ─── Build solo OpenAlex MCP ──────────────────────────────────────────────────
build-openalex:
	@echo "▶  Building OpenAlex MCP image..."
	docker build -t multi-servicesproject-openalex-mcp "$(PROJECT_ROOT)/MCPs/OpenAlex MCP"

# ─── Detener todo ─────────────────────────────────────────────────────────────
down:
	@echo "▶  Stopping MCPs (DSpace + MinIO)..."
	$(COMPOSE) stop
	@echo "▶  Stopping external services (Bots Detector)..."
	$(BOTS_COMPOSE) down

# ─── Logs en tiempo real ──────────────────────────────────────────────────────
logs:
	$(COMPOSE) logs -f

# ─── Reiniciar solo los MCPs ──────────────────────────────────────────────────
restart:
	$(COMPOSE) restart
