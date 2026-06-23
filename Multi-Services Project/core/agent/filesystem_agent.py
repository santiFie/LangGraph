"""
Filesystem Agent: Agent for filesystem operations
Enables interaction with repositories, create/edit files, make commits
Supports interrupts for commit confirmation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from core.utils.config import config
from core.utils.prompt_loader import load_agent_prompt


class FilesystemState(TypedDict):
    """State for the Filesystem agent"""
    messages: Annotated[list[BaseMessage], add_messages]


async def build_filesystem_workflow(tools):
    """
    Builds the filesystem agent graph
    
    Args:
        tools: List of tools loaded from MCP (filesystem)
        
    Returns:
        Compiled agent graph
    """
    filesystem_model = ChatGoogleGenerativeAI(
        model=config.FILESYSTEM_MODEL,
        temperature=0
    ).bind_tools(tools=tools)

    async def filesystem_agent_node(state: FilesystemState):
        """Agent node that handles filesystem operations"""

        sys_msg = load_agent_prompt(
            "filesystem_agent",
            WORKSPACE_PATH=config.WORKSPACE_PATH,
            DOWNLOADS_DIR=config.DOWNLOADS_DIR,
        )
        prompt = [SystemMessage(content=sys_msg)] + state["messages"]
        
        response = await filesystem_model.ainvoke(prompt)

        # Normalizar respuesta a un objeto de mensaje válido
        if isinstance(response, dict):
            content = response.get("content") or response.get("text") or str(response)
            response_msg = AIMessage(content=content)
        elif isinstance(response, BaseMessage):
            response_msg = response
        else:
            response_msg = AIMessage(content=str(response))

        return {"messages": [response_msg]}

    workflow = StateGraph(FilesystemState)
    
    # Nodes
    workflow.add_node("agent", filesystem_agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    # Edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
    )
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(name="FilesystemGraph")
