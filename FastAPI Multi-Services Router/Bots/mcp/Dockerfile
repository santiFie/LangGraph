FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Using standard MCP stdio for simplicity if used in docker, or SSE? 
# Usually MCP servers run via stdio. Or we can use FastMCP SSE.
# FastMCP can run a SSE server:
CMD ["python", "server.py"]
