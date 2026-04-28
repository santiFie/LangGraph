# Bots MCP & API Server

This project provides a FastAPI backend to manage bot attack records in a SQLite database, along with a FastMCP server to expose these operations as tools for AI agents (e.g., a LangGraph Agent).

## Architecture

* **Database**: SQLite database storing records with parameters: `ip`, `last_attack`, `blocked_window`, and `num_attacks`.
* **API**: FastAPI providing endpoints to retrieve bot records and report new attacks. Runs on port `8000`.
* **MCP Server**: FastMCP server acting as a bridge. It exposes tools via SSE to interact with the API. Runs on port `8001`.

## Database Schema (Bots)

- `ip`: IP Address of the bot (String).
- `last_attack`: Timestamp of the last attack (DateTime).
- `blocked_window`: Number of days the IP is blocked. Increments on repeated attacks (Integer).
- `num_attacks`: Total number of reported attacks for the IP (Integer).

The database comes pre-seeded with 20 dummy records.

## Endpoints (API)

* `GET /bots/`: Retrieves all bot records (default limit 20).
* `GET /bots/{ip}`: Retrieves the bot record matching the specified IP.
* `POST /bots/report`: Accepts `{"ip": "..."}`. If it exists, increments `num_attacks` and `blocked_window`. If not, creates a new record.

## MCP Server Tools

The MCP Server provides the following tools:
1. `get_all_bots`: Fetches all bot attack records.
2. `get_bot_by_ip`: Fetch connection statistics/metadata for a single IP.
3. `report_bot`: Reports a bot attack, triggering blocking incrementation.

## Getting Started

1. Ensure you have Docker and Docker Compose installed.
2. Run the application:
   ```bash
   docker-compose up --build
   ```
3. Access the API Docs at `http://localhost:8000/docs`.
4. Connect your LangGraph agent or MCP Client to the SSE MCP server at `http://localhost:8001/sse`.

## LangGraph Integration

When using LangGraph, connect the FastMCP client to the SSE address (`http://127.0.0.1:8001/sse`). 
The Agent can then call `get_all_bots`, `get_bot_by_ip`, or `report_bot` seamlessly via MCP.
