"""
Main Supervisor Graph
Orchestrates the three specialized subgraphs:
- Searcher: Search with RAG and web search
- Bots: Bot attack analysis
- GitHub: Repository and filesystem operations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from contextlib import AsyncExitStack
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph_supervisor import create_supervisor
import warnings

from core.agent.researcher import build_searcher_graph
from core.agent.bots_agent import build_bots_workflow
from core.agent.github_agent import build_github_workflow
from core.utils.config import config

warnings.filterwarnings("ignore")


async def create_supervisor_graph(persistence_saver):
    """
    Creates the supervisor graph that coordinates the three agents
    Requires all MCP sessions to be active
    
    Args:
        persistence_saver: Checkpoint saver for state persistence
        
    Returns:
        Compiled supervisor graph
    """
    
    # Initialize MCP client for Bots
    bots_client = MultiServerMCPClient(
        {
            "BotsAgent": {
                "url": config.BOTS_MCP_URL,
                "transport": "sse"
            }
        }
    )
    
    # MCP client for GitHub and Filesystem
    system_env = dict(os.environ)
    github_env = {
        **system_env,
        "GITHUB_PERSONAL_ACCESS_TOKEN": config.GITHUB_PERSONAL_ACCESS_TOKEN or ""
    }
    
    github_client = MultiServerMCPClient(
        {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", config.WORKSPACE_PATH],
                "transport": "stdio",
                "env": system_env
            },
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": github_env,
                "transport": "stdio",
            }
        }
    )
    
    async with AsyncExitStack() as stack:
        # 1) Open all sessions
        bots_session = await stack.enter_async_context(bots_client.session("BotsAgent"))
        github_session = await stack.enter_async_context(github_client.session("github"))
        filesystem_session = await stack.enter_async_context(github_client.session("filesystem"))
        
        # 2) Load tools for all subgraphs
        bot_tools = await load_mcp_tools(bots_session)
        github_tools = await load_mcp_tools(github_session)
        filesystem_tools = await load_mcp_tools(filesystem_session)
        
        # 3) Build/compile subgraphs with their respective tools
        searcher_graph = build_searcher_graph()
        bots_graph = build_bots_workflow(bot_tools)
        github_graph = await build_github_workflow(github_tools + filesystem_tools)
        
        # 4) Create the supervisor graph
        supervisor_model = ChatOpenAI(
            model="z-ai/glm-5.1",
            api_key=config.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1", # NVIDIA's API URL
            temperature=0.0,
        )
        
        supervisor_graph = create_supervisor(
            model=supervisor_model,
            agents=[searcher_graph, bots_graph, github_graph],
            prompt=(
                "You are a supervisor that routes tasks to specialized subgraphs: "
                "- 'searcher' for answering questions using retrieved documents about deep learning or searching in the internet, "
                "- 'bots' for answering questions related to bots attacks logs, "
                "- 'github' for answering questions related to GitHub repositories and filesystem operations. "
            )
        ).compile(name="SupervisorGraph", checkpointer=persistence_saver)
        
        return supervisor_graph


# Para uso en LangServe, crear un builder síncrono
def get_supervisor_graph(persistence_saver=None):
    """
    Retorna el grafo supervisor para uso en LangServe
    Nota: En producción, esto debería ser cacheado
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(create_supervisor_graph(persistence_saver))
