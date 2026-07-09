import asyncio
import os
import sqlite3
from typing import Annotated, Any, TypedDict, cast
from typing import Any, TypedDict, cast
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph_supervisor import create_supervisor
from core.agent.bots_agent import build_bots_workflow
from core.agent.filesystem_agent import build_filesystem_workflow
from core.agent.researcher_agent import build_searcher_graph
from core.agent.dspace_agent import build_dspace_agent_workflow
from core.agent.minio_agent import build_minio_workflow
from core.utils.config import config


async def create_supervisor_graph(persistence_saver):
    """
    Creates the supervisor graph that coordinates the three agents.
    Requires all MCP sessions to be active.
    """

    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]

    system_env = dict(os.environ)
    filesystem_client = MultiServerMCPClient(
        {
            "filesystem": {
                "command": "mcp-server-filesystem",
                "args": [config.WORKSPACE_PATH],
                "transport": "stdio",
                "env": system_env,
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

    filesystem_tools = await filesystem_client.get_tools(server_name="filesystem")
    dspace_tools = await dspace_client.get_tools(server_name="DspaceMCP")
    minio_tools = await minio_client.get_tools(server_name="aistor")

    def _build_searcher_sync():
        return build_searcher_graph()

    searcher_graph = _build_searcher_sync()
    filesystem_graph = await build_filesystem_workflow(filesystem_tools)
    dspace_graph = await build_dspace_agent_workflow(dspace_tools)
    minio_graph = await build_minio_workflow(minio_tools)

    supervisor_model = ChatGroq(model=config.SUPERVISOR_MODEL, temperature=0)


    def metadata_generator(state: State):
        default_metadata = {
            "dc.date.issued": "2026-06-25",
            "dc.date.created": "2026-06-25",
            "dc.subject": "Matematica",
            "dc.language": "es-ES",
            "dc.identifier": "123456789",
            "dc.creator": "Juan Perez",
            "sedici.subtype": "Mi primer dataset",
            "dc.description.abstract": "Este es un dataset de ejemplo",
        }
        return default_metadata

    workflow = StateGraph()

    # Nodes
    workflow.add_node("dspace", dspace_graph)
    workflow.add_node("minio", minio_graph)
    workflow.add_node("filesystem", filesystem_graph)

    workflow.add_node("final_answer_node", final_answer_node)
    

    # Edges
    workflow.add_edge(START, "rag_context")
    workflow.add_edge("rag_context", "planner")
    workflow.add_conditional_edges("planner", route_current_task, {
        "searcher": "searcher",
        "filesystem": "filesystem",
        "bots": "bots",
        "dspace": "dspace",
        "minio": "minio",
        "openalex": "openalex",
        "replanner": "replanner"
    })

    for agent in ["searcher", "filesystem", "bots", "dspace", "minio", "openalex"]:
        workflow.add_edge(agent, "replanner")

    workflow.add_conditional_edges(
        "replanner",
        route_current_task,
        {
            "searcher": "searcher",
            "filesystem": "filesystem",
            "bots": "bots",
            "dspace": "dspace",
            "minio": "minio",
            "openalex": "openalex",
            "final_answer_node": "final_answer_node"
        }
    )

    workflow.add_edge("final_answer_node", END)

    return workflow.compile(name="SupervisorGraph")

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