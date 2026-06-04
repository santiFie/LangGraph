.PHONY: up down studio studio-url open-studio

# Levantamos el container proxy (API de Bots / MCP Server), seguido de Langgraph dev
up:
	@echo "Starting MCPs"
	docker compose -f "/home/santi/Documentos/Prebi/bots-detector/docker-compose.yml" up -d
	docker compose -f "../Multi-Services Project/MCPs/Dspace MCP/docker-compose.yml" up -d
	docker compose -f "../Multi-Services Project/MCPs/MinIO MCP/docker-compose.yml" up -d
	@echo "Iniciando LangGraph Platform local..."
	LANGGRAPH_STARTUP_TIMEOUT=30 langgraph dev --allow-blocking

build:
	@echo "Building MCPs"
	docker compose -f "/home/santi/Documentos/Prebi/bots-detector/docker-compose.yml" build
	docker compose -f "../Multi-Services Project/MCPs/Dspace MCP/docker-compose.yml" build
	docker compose -f "../Multi-Services Project/MCPs/MinIO MCP/docker-compose.yml" build

# Detenemos LangGraph (mediante interrupción local) y apagamos el container proxy
down:
	@echo "Stopping MCPs"
	docker compose -f "/home/santi/Documentos/Prebi/DSpace/docker/docker-compose.yml" stop
	docker compose -f "/home/santi/Documentos/Prebi/bots-detector/docker-compose.yml" down
	docker compose -f "../Multi-Services Project/MCPs/Dspace MCP/docker-compose.yml" down
	docker compose -f "../Multi-Services Project/MCPs/MinIO MCP/docker-compose.yml" down
