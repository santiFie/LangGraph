import asyncio
import os
import sqlite3
from typing import Any, TypedDict, cast
from typing import Any, TypedDict, cast
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph_supervisor import create_supervisor
from core.agent.bots_agent import build_bots_workflow
from core.agent.github_agent import build_github_workflow
from core.agent.researcher_agent import build_searcher_graph
from core.agent.dspace_agent import build_dspace_agent_workflow
from core.agent.minio_agent import build_minio_workflow
from core.utils.config import config


async def create_supervisor_graph(persistence_saver):
    """
    Creates the supervisor graph that coordinates the three agents.
    Requires all MCP sessions to be active.
    """
    bots_client = MultiServerMCPClient(
        {
            "BotsAgent": {
                "url": config.BOTS_MCP_URL.replace("mcp", "127.0.0.1"),
                "transport": "sse",
            }
        }
    )

    system_env = dict(os.environ)
    github_env = {
        **system_env,
        "GITHUB_PERSONAL_ACCESS_TOKEN": config.GITHUB_PERSONAL_ACCESS_TOKEN or "",
    }

    github_client = MultiServerMCPClient(
        {
            "filesystem": {
                "command": "mcp-server-filesystem",
                "args": [config.WORKSPACE_PATH],
                "transport": "stdio",
                "env": system_env,
            },
            "github": {
                "command": "mcp-server-github",
                "args": [],
                "env": github_env,
                "transport": "stdio",
            },
        }
    )

    dspace_client = MultiServerMCPClient(
        {
            "DspaceMCP": {
                "url": config.DSPACE_MCP_URL,
                "transport": "sse",
            }
        }
    )

    DOWNLOADS_DIR = config.DOWNLOADS_DIR
    MINIO_ACCESS_KEY = config.MINIO_ROOT_USER
    MINIO_SECRET_KEY = config.MINIO_ROOT_PASSWORD

    minio_client = MultiServerMCPClient(
        {
            "aistor": {
                "command": "docker",
                "args": [
                    "run",
                    "-i",
                    "--rm",
                    "--network=host",
                    "-v", f"{DOWNLOADS_DIR}:/Downloads",
                    "-e", "MINIO_ENDPOINT=localhost:9003", 
                    "-e", f"MINIO_ACCESS_KEY={MINIO_ACCESS_KEY}",
                    "-e", f"MINIO_SECRET_KEY={MINIO_SECRET_KEY}",
                    "-e", "MINIO_USE_SSL=false",
                    "quay.io/minio/aistor/mcp-server-aistor:latest",
                    "--allowed-directories", "/Downloads",
                    "--allow-write",
                    "--allow-delete",
                    "--allow-admin"
                ],
                "transport": "stdio",
            },
        }
    )

    bot_tools = await bots_client.get_tools()
    github_tools = await github_client.get_tools(server_name="github")
    filesystem_tools = await github_client.get_tools(server_name="filesystem")
    dspace_tools = await dspace_client.get_tools(server_name="DspaceMCP")
    minio_tools = await minio_client.get_tools(server_name="aistor")

    def _build_searcher_sync():
        return build_searcher_graph()

    searcher_graph = _build_searcher_sync()
    github_graph = await cast(Any, build_github_workflow(github_tools + filesystem_tools))
    bots_graph = build_bots_workflow(bot_tools)
    dspace_graph = await build_dspace_agent_workflow(dspace_tools)
    minio_graph = await build_minio_workflow(minio_tools)

    supervisor_model = ChatGroq(model=config.SUPERVISOR_MODEL, temperature=0)

    return create_supervisor(
            model=supervisor_model,
            agents=[searcher_graph, bots_graph, github_graph, dspace_graph, minio_graph],
            prompt = f"""
            You are a supervisor that routes tasks to specialized subgraphs. 
            CRITICAL: You must decompose tasks. Agents do not share tools, but they share a local directory: {DOWNLOADS_DIR}

            To upload a local system file to MinIO, you MUST follow this strict sequence:
            1. Store the requested file in the shared directory: {DOWNLOADS_DIR}.
                1.1) If the file is not already in {DOWNLOADS_DIR}, use the 'github' agent's filesystem tools to copy or move it there. Do NOT attempt to interact with MinIO directly to access files outside of {DOWNLOADS_DIR}.
                1.2) If the file can be generated directly in {DOWNLOADS_DIR} by any agent, instruct that agent to do so. For example, if the file is a CSV export of DSpace metadata, instruct the 'dspace' agent to save the export directly into {DOWNLOADS_DIR}.
            2. Once confirmed, route to the 'minio' agent and instruct it to upload that file to the required bucket.

            Agent capabilities and constraints:
            - 'searcher': Documents and internet search.
            - 'bots': Bot attacks logs analysis.
            - 'github': GitHub repositories management and local filesystem operations. Use this agent if a file needs to be moved or prepared into {DOWNLOADS_DIR}.
            - 'dspace': SEDICI (DSpace) repositories administration.
            - 'minio': MinIO file storage management. CRITICAL: This agent operates isolated and can ONLY read/write files that are already inside its internal '/Downloads' mount (which maps to {DOWNLOADS_DIR} on the host). It cannot access files outside this directory.

            IMPORTANT: When you have the complete answer or confirmation that the task was successfully finished by the sub-agents, return it to the user.
            """
        ).compile(name="SupervisorGraph", checkpointer=persistence_saver)


def get_supervisor_graph(persistence_saver=None):
    """Returns the supervisor graph for synchronous usage."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(create_supervisor_graph(persistence_saver))

def _load_supervisor_graph():
    try:
        return get_supervisor_graph(None)
    except Exception as exc:
        raise RuntimeError("Failed to create the supervisor graph", exc)


supervisor_graph = _load_supervisor_graph()