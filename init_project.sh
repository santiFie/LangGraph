source .venv/bin/activate;

cd /home/santi/Documentos/Prebi/llm-orchestrator;
docker compose up -d;


docker compose -f "/home/santi/Documentos/Prebi/DSpace/docker/docker-compose.yml" up -d;

sleep 15;

cd /home/santi/Documentos/LangGraph/Multi-Services\ Project;


make up
