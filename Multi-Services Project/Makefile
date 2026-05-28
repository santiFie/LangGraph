.PHONY: up down studio studio-url open-studio

# Levantamos el container proxy (API de Bots / MCP Server), seguido de Langgraph dev
up:
	@echo "Iniciando infraestructura de apoyo externo (Bots MCP Server)..."
	docker compose -f "../FastAPI Multi-Services Router/Bots/docker-compose.yml" up -d
	@echo "Iniciando LangGraph Platform local..."
	LANGGRAPH_STARTUP_TIMEOUT=30 langgraph dev --allow-blocking

# Detenemos LangGraph (mediante interrupción local) y apagamos el container proxy
down:
	@echo "Deteniendo infraestructura de apoyo externo (Bots MCP Server)..."
	docker compose -f "../FastAPI Multi-Services Router/Bots/docker-compose.yml" down
