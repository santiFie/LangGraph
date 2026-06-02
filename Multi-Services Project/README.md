# Multi-Services Project

## Description
Multi-service project that integrates components and MCPs (Microservice Control Points) on the LangGraph platform. It contains the core set of tools, agents, and adapters used by the application, along with examples for running Studio and local MCPs.

## Requirements
- **Python 3.9+** (recommended)

- **Virtualenv** or a similar environment

- **Dependencies:** install via pip install -r requirements.txt from the root of this folder.

## Quick Installation
Create and activate a virtual environment:

`python -m venv .venv`

`source .venv/bin/activate`

`pip install -r requirements.txt`

## Useful commands:

To start de app with containers:

`make up`


## Run tests:

`pytest -q`

## Connecting to LangGraph Studio

If auth is on:

### Authentication
Configure Studio to send the X-API-Key header with the token defined in your environment (e.g., secure_token_123).

## Main Structure

**.langgraph_api/:** checkpoints and local LangGraph state

**core/:** core code (agents, tools, authentication)

**agent/:** agent implementations (bots, dspace, github, researcher)

**tools/:** utilities and retrievers

**security/:** auth handling

**MCPs/:** MCPs and auxiliary services (e.g., Dspace MCP)

**rag_pdfs/:** RAG resources

**tests/:** unit and integration tests

### Development

*Key files:*

**core/graph.py** — main graph logic

**core/agent** — agents and integration examples

**MCPs/ Dspace MCP/src** — client and utilities for Dspace

### Local execution
Check the scripts inside each subfolder (e.g., MCPs/Dspace MCP/src/main.py) and run them with the virtual environment activated.

## Best Practices

- Use a virtual environment to avoid dependency conflicts.

- Keep credentials out of the repository and use environment variables or a .env file for development purposes only.

- Run pytest before opening PRs.

## Contributing

- Open an issue or a branch for each feature or bug.

- Ensure tests pass and add tests for any relevant changes.

- Submit a PR with a clear description and reproduction steps.

## Contact
For questions regarding local configuration or execution, open an issue in the repository or contact the project maintainer.