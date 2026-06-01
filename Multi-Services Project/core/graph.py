import asyncio
import os
import sqlite3
from typing import Any, TypedDict, cast
from typing import Any, TypedDict, cast
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph_supervisor import create_supervisor
from core.agent.bots_agent import build_bots_workflow
from core.agent.github_agent import build_github_workflow
from core.agent.researcher import build_searcher_graph
from core.agent.dspace_agent import build_dspace_agent_workflow
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

    bot_tools = await bots_client.get_tools()
    github_tools = await github_client.get_tools(server_name="github")
    filesystem_tools = await github_client.get_tools(server_name="filesystem")
    dspace_tools = await dspace_client.get_tools(server_name="DspaceMCP")

    def _build_searcher_sync():
        return build_searcher_graph()

    searcher_graph = _build_searcher_sync()
    github_graph = await cast(Any, build_github_workflow(github_tools + filesystem_tools))
    bots_graph = build_bots_workflow(bot_tools)
    dspace_graph = build_dspace_agent_workflow(dspace_tools)

    supervisor_model = ChatGroq(model=config.SEARCHER_MODEL, temperature=0)
    
    return create_supervisor(
        model=supervisor_model,
        agents=[searcher_graph, bots_graph, github_graph, dspace_graph],
        prompt=(
            "You are a supervisor that routes tasks to specialized subgraphs: "
            "- 'searcher' for answering questions using retrieved documents about deep learning or searching in the internet, "
            "- 'bots' for answering questions related to bots attacks logs, "
            "- 'github' for answering questions related to GitHub repositories and filesystem operations. "
            "- 'dspace' for answering questions related to DSpace repositories. The dspace app is called SEDICI."
        )
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