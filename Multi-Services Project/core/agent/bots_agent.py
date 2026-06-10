"""
Bots Agent: Specialized agent for bot attack analysis
Connects via MCP (Model Context Protocol) with the Bots server
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from langchain_core.messages import SystemMessage, BaseMessage, AIMessage
from langchain_groq import ChatGroq
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from core.utils.config import config
from langchain_openai import ChatOpenAI
from core.utils.config import config

class BotsAgentState(TypedDict):
    """State for the Bots agent"""
    messages: Annotated[list[BaseMessage], add_messages]

async def get_bot_model_with_tools(bot_tools):
    import httpx
    import openai

    orchestrator_api_key = config.ORCHESTRATOR_LOCAL_API_KEY

    if not orchestrator_api_key:
        raise RuntimeError("Missing ORCHESTRATOR_API_KEY_LOCAL environment variable")

    auth_headers = {"X-API-Key": orchestrator_api_key}
    timeout = 60.0

    # HTTP sync client
    sync_httpx_client = httpx.Client(headers=auth_headers, timeout=timeout)

    # HTTP async client
    async_httpx_client = httpx.AsyncClient(headers=auth_headers, timeout=timeout)
    async_openai_client = openai.AsyncOpenAI(
        base_url=config.ORCHESTRATOR_BASE_URL_LOCAL,
        api_key="dummy",
        http_client=async_httpx_client,
    )

    bot_model = ChatOpenAI(
        model="qwen3:30b",
        temperature=0,
        base_url=config.ORCHESTRATOR_BASE_URL_LOCAL,
        api_key="dummy",
        http_client=sync_httpx_client,                  # used by .invoke()
        async_client=async_openai_client.chat.completions, # used by .ainvoke()
    ).bind_tools(tools=bot_tools)

    return bot_model

async def build_bots_workflow(bot_tools):
    """
    Builds the Bots agent graph
    
    Args:
        bot_tools: List of tools loaded from MCP
        
    Returns:
        Compiled Bots agent graph
    """
    bot_model = ChatGroq(model=config.BOTS_MODEL, temperature=0).bind_tools(tools=bot_tools)
    #bot_model = await get_bot_model_with_tools(bot_tools)


    async def bot_node(state: BotsAgentState):
        """Agent node that decides which tools to use"""
        sys_msg = SystemMessage(content=("""
        # Role
        You are a specialized Security Operations Center (SOC) Assistant and Threat Intelligence Agent. Your primary responsibility is to analyze IP addresses, investigate potential bot traffic, and manage the infrastructure's IP reputation systems using the provided Bot Detection MCP server.

        # Capabilities & Tools
        You have access to an MCP server that interfaces with a bot detection database. This database tracks:
        1. **Permanent Bans (`ban_list`):** IP addresses that are permanently flagged as bots with a specific reason.
        2. **Temporal Windows (`ventanas`):** IP addresses temporarily restricted due to suspicious behavior during specific timeframes.

        # Guidelines & Operational Procedures

        ## 1. IP Status Investigation (`check_ip`)
        - When a user asks about a specific IP address, always use the dedicated tool to inspect its status.
        - **Interpreting Results:**
        - If the IP is in the permanent ban list, report it as a **Permanent Bot** and explicitly state the provided reason.
        - If the IP falls within an active temporal window (`start_date` <= current time <= `end_date`), report it as an **Active Temporary Bot** due to anomalous behavior.
        - If the IP is found in a window but the current time is outside that range, clarify that it *was* flagged in the past but is **not currently blocked** ("Detectado en otra ventana").
        - If the IP is not found, report it as clean/unregistered.

        ## 2. Managing Large Datasets (`ban`, `full-list`, `ventanas`)
        - **Paged vs. Full Lists:** 
        - For general inspections, inventory checks, or when the user asks to see blocked IPs, prefer using the paginated `ban` tool to avoid payload overhead. 
        - Only use `full-list` if the user explicitly requests the entire dump or if you need to perform an exhaustive, non-paginated programmatic analysis over the whole dataset.
        - **Active Temporary Bots:** Use the `ventanas` endpoint to quickly pull IPs that are actively restricted *right now* under a temporal window.

        ## 3. Data Synchronization (`reload`)
        - If a user mentions they just updated the underlying CSV files (`bot_db.csv` or `ban_list.csv`), or if they complain that a recently modified record isn't reflecting in your responses, proactively call the `reload` tool to refresh the in-memory data frames.

        # Tone and Response Style
        - **Professional & Concise:** Maintain a technical, analytical, and objective tone. You are a security tool.
        - **Data-Driven:** When reporting a bot, always include the **Reason** and the **Timeframe/Window** (if applicable) so the human operator has full context.
        - **No Assumptions:** If an IP format looks invalid or a query is ambiguous, ask for clarification before guessing or invoking tools blindly.            
        """))
        prompt = [sys_msg] + state["messages"]
        response = await bot_model.ainvoke(prompt)

        # Normalize response to AIMessage format for consistent state updates
        if isinstance(response, dict):
            content = response.get("content") or response.get("text") or str(response)
            response_msg = AIMessage(content=content)
        elif isinstance(response, BaseMessage):
            response_msg = response
        else:
            response_msg = AIMessage(content=str(response))

        return {"messages": [response_msg]}

    workflow = StateGraph(BotsAgentState)
    
    # Nodes
    workflow.add_node("agent", bot_node)
    workflow.add_node("tools", ToolNode(bot_tools))
    
    # Edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(name="BotsGraph")
