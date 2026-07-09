"""
Database Agent: Specialized agent for database analysis
Connects via MCP (Model Context Protocol) with the Database server

System prompt is loaded at runtime from agent_prompts/database_agent.md.
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
from core.utils.prompt_loader import load_agent_prompt
from langchain_openai import ChatOpenAI
from core.utils.get_local_model import get_local_model
# Set to True to use local Ollama model, False to use remote OpenAI model
USE_LOCAL_MODEL = False

class DatabaseAgentState(TypedDict):
    """State for the Database agent"""
    messages: Annotated[list[BaseMessage], add_messages]

async def _get_model():
  """Returns the appropriate model instance based on the USE_LOCAL_MODEL flag."""
  if USE_LOCAL_MODEL:
      model = await get_local_model()
  else:
      model = ChatOpenAI(
          model=config.DATABASE_MODEL,
          api_key=config.OPEN_ROUTER_API_KEY,
          base_url=config.OPEN_ROUTER_BASE_URL,
          temperature=0,
      )
  return model

async def build_database_workflow(database_tools):
    """
    Builds the database agent graph
    
    Args:
        database_tools: List of tools loaded from MCP
        
    Returns:
        Compiled database agent graph
    """
    model = await _get_model()
    model = model.bind_tools(tools=database_tools)

    async def database_node(state: DatabaseAgentState):
        """Agent node that decides which tools to use"""
        sys_msg = SystemMessage(content=load_agent_prompt("database_agent"))
        prompt = [sys_msg] + state["messages"]
        response = await model.ainvoke(prompt)

        if isinstance(response, dict):
            content = response.get("content") or response.get("text") or str(response)
            response_msg = AIMessage(content=content)
        elif isinstance(response, BaseMessage):
            response_msg = response
        else:
            response_msg = AIMessage(content=str(response))

        return {"messages": [response_msg]}

    workflow = StateGraph(DatabaseAgentState)
    
    # Nodes
    workflow.add_node("agent", database_node)
    workflow.add_node("tools", ToolNode(database_tools))
    
    # Edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(name="DatabaseGraph")
