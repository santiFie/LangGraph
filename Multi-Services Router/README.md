# Multi-Services Router - FastAPI Deployment

A production-ready, intelligent service router built with LangGraph, FastAPI, and LangChain. Orchestrates three specialized agents for Deep Learning search, bot attack analysis, and GitHub operations.

## 🚀 Features

- **Intelligent Routing**: Supervisor agent automatically routes requests to the appropriate specialized agent
- **Deep Learning Search**: RAG-powered search with ChromaDB + Tavily web search
- **Bot Analysis**: Specialized agent for analyzing bot attacks and security logs
- **GitHub Integration**: Full GitHub repository and filesystem operations via MCP
- **Production Ready**: 
  - Docker Compose for easy deployment
  - SQLite persistence with async support
  - LangGraph Studio integration for visualization
  - Health checks and monitoring
  - Structured logging
- **API First**: FastAPI REST API with streaming support

## 📋 Requirements

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- GNU Make
- Node.js 18+ (for MCP servers)
- API Keys:
  - OpenAI (for supervisor model)
  - Groq (for search agent)
  - Google Gemini (for GitHub agent)
  - Tavily (for web search)
  - GitHub Token (for repository operations)

## 🔧 Installation

### Option 1: Local Development

1. **Clone and navigate to the project**
```bash
cd "Multi-Services Router"
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
nano .env
```

5. **Prepare PDFs for RAG**
```bash
# Place your PDF files in the rag_pdfs directory
mkdir -p "rag_pdfs"
# Copy your PDFs here
```

6. **Run the application**
```bash
# Direct execution
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/docs` for API documentation.

### Option 2: Docker Compose Deployment

1. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
nano .env
```

2. **Prepare PDFs**
```bash
mkdir -p "rag_pdfs"
# Copy your PDFs here
```

3. **Build and run**
```bash
make up
```

4. **Access services**
- **API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Bots MCP**: http://localhost:8001/sse

## 📖 API Usage

### Invoke the Supervisor

```bash
curl -X POST http://localhost:8000/supervisor/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [{"type": "human", "content": "What is deep learning?"}]
    }
  }'
```

### Stream Responses

```bash
curl -X POST http://localhost:8000/supervisor/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "messages": [{"type": "human", "content": "What is deep learning?"}]
    }
  }'
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/supervisor/batch \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [
      {"messages": [{"type": "human", "content": "Query 1"}]},
      {"messages": [{"type": "human", "content": "Query 2"}]}
    ]
  }'
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         FastAPI App                         │
│  (main.py - HTTP/REST Interface)            │
└────────────────┬────────────────────────────┘
                 │
┌─────────────────▼────────────────────────────┐
│         Supervisor Graph                     │
│  (Routes to specialized agents)              │
└─┬──────────────────────┬────────────────────┬┘
  │                      │                    │
  ▼                      ▼                    ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Searcher     │  │ Bots         │  │ GitHub       │
│ Agent        │  │ Agent        │  │ Agent        │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ • RAG        │  │ • MCP Tools  │  │ • MCP        │
│ • Web Search │  │ • Analysis   │  │ • Filesystem │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 📁 Project Structure

```
Multi-Services Router/
├── main.py                          # FastAPI entry point
├── Dockerfile                       # Container image
├── docker-compose.yml               # Multi-container orchestration
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── langgraph.json                   # LangGraph Studio config
├── checkpoint.db                    # Persistent state database
├── rag_pdfs/                        # PDF knowledge base
├── core/
│   ├── __init__.py
│   ├── graph.py                     # Supervisor graph
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── researcher.py            # Searcher agent (RAG + web)
│   │   ├── bots_agent.py            # Bot analysis agent
│   │   └── github_agent.py          # GitHub operations agent
│   ├── tools/
│   │   ├── retriever.py             # RAG retriever setup
│   │   └── tavily.py                # Web search tool
│   └── utils/
│       ├── __init__.py
│       └── config.py                # Centralized configuration
├── Bots/
│   ├── api/                         # Bots MCP server
│   ├── README.md
│   └── docker-compose.yml
└── tests/                           # Unit tests
```

## 🔑 Environment Variables

Essential variables in `.env`:

```bash
# LLM Providers
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
NVIDIA_API_KEY=your_key

# Search
TAVILY_API_KEY=your_key

# GitHub
GITHUB_PERSONAL_ACCESS_TOKEN=your_token

# Paths
WORKSPACE_PATH=/path/to/workspace
RAG_PDF_PATH=./rag_pdfs

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Persistence
CHECKPOINT_DB=checkpoint.db
```

See `.env.example` for all available options.

## 🚀 LangGraph Studio Integration

To visualize and debug your graphs:

1. **Install LangGraph CLI** (if not already done)
```bash
pip install langgraph-cli
```

2. **Run LangGraph Studio**
```bash
langgraph up
```

3. **Access Studio**
Visit `http://localhost:8000` in your browser

The studio provides:
- Visual graph representation
- Step-by-step execution debugging
- Message flow visualization
- State inspection
- Breakpoint support

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "checkpoint.db"
}
```

### Logs

Local:
```bash
tail -f logs/app.log
```

Docker:
```bash
docker logs -f multi-services-router
```

## 🧪 Testing

Run tests:
```bash
pytest tests/
```

With coverage:
```bash
pytest --cov=core tests/
```

## 🔄 Agents Explained

### 1. Searcher Agent
- **Purpose**: Answer questions using RAG and web search
- **Tools**: 
  - Deep Learning RAG retriever (ChromaDB)
  - Tavily web search
- **Flow**: Author → Tools → Reviewer → (Repeat or End)

### 2. Bots Agent
- **Purpose**: Analyze bot attacks and security logs
- **Tools**: MCP-based tools from Bots API
- **Integration**: SSE transport for real-time data

### 3. GitHub Agent
- **Purpose**: Manage repositories and filesystem operations
- **Tools**: GitHub and Filesystem MCP servers
- **Features**: File creation, editing, commits with approval workflow

## 🐛 Troubleshooting

### MCP Server Connection Failed
```
Error: Failed to connect to MCP server
```
**Solution**: Ensure Bots MCP is running and accessible at `BOTS_MCP_URL` (`http://localhost:8001/sse`)

### Database Lock Error
```
Error: database is locked
```
**Solution**: Only one process should access checkpoint.db at a time. Restart the application.

### PDF Not Found in RAG
```
FileNotFoundError: No PDF files found in ./rag_pdfs/*.pdf
```
**Solution**: Create `rag_pdfs` directory and add PDF files:
```bash
mkdir -p "rag_pdfs"
cp your_pdfs.pdf "rag_pdfs"/
```

### Memory Issues with Large PDFs
**Solution**: Adjust in `config.py`:
```python
CHUNK_SIZE = 1000  # Reduce from 1500
CHUNK_OVERLAP = 100  # Reduce from 200
```

## 📈 Performance Tuning

### For High Throughput
```bash
# Increase workers with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### For Low Latency
```bash
# Enable HTTP/2
uvicorn main:app --http h2c --host 0.0.0.0 --port 8000
```

### Database Optimization
```python
# Batch checkpoint saves
CHECKPOINT_BATCH_SIZE = 10
```

## 🔐 Security Considerations

- **API Keys**: Never commit `.env` to version control
- **GitHub Token**: Use fine-grained personal access tokens
- **Rate Limiting**: Implement at reverse proxy level (nginx, Traefik)
- **CORS**: Configure allowed origins in production
- **HTTPS**: Use reverse proxy with SSL/TLS

## 📝 License

[Your License Here]

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation
- Review the troubleshooting section

## 🔗 References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 📊 Status

- ✅ Core agents implemented
- ✅ FastAPI integration
- ✅ Docker deployment
- ✅ LangGraph Studio support
- ✅ Persistence layer
- ⏳ Advanced monitoring (Prometheus metrics)
- ⏳ Kubernetes deployment manifests

---

Built with ❤️ using LangGraph, FastAPI, and LangChain
