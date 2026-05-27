.PHONY: up down

# Levantamos el container proxy (API de Bots / MCP Server), seguido de Langgraph dev
up:
	@echo "Iniciando infraestructura de apoyo externo (Bots MCP Server)..."
	docker compose -f "../Multi-Services Router/Bots/docker-compose.yml" up -d
	@echo "Iniciando LangGraph Platform local..."
	langgraph dev --host 127.0.0.1 --port 2024

# Detenemos LangGraph (mediante interrupción local) y apagamos el container proxy
down:
	@echo "Deteniendo infraestructura de apoyo externo (Bots MCP Server)..."
	docker compose -f "../Multi-Services Router/Bots/docker-compose.yml" down
