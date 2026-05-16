"""
Bots Agent: Specialized agent for bot attack analysis
Connects via MCP (Model Context Protocol) with the Bots server
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from langchain_core.messages import SystemMessage, BaseMessage
from langchain_groq import ChatGroq
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from core.utils.config import config


class BotsAgentState(TypedDict):
    """State for the Bots agent"""
    messages: Annotated[list[BaseMessage], add_messages]


def build_bots_workflow(bot_tools):
    """
    Builds the Bots agent graph
    
    Args:
        bot_tools: List of tools loaded from MCP
        
    Returns:
        Compiled Bots agent graph
    """
    bot_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0).bind_tools(tools=bot_tools)

    async def bot_node(state: BotsAgentState):
        """Agent node that decides which tools to use"""
        sys_msg = SystemMessage(content=(
            "You are a specialist assistant in analyzing bot attacks. "
            "Your goal is to help users understand and mitigate attacks. "
            "You have access to tools that allow you to query attack logs, "
            "suspicious IPs, attack patterns, etc. "
            "If the user asks for sensitive information (like IPs), respond securely. "
            "If the question is not related to bots, answer the user directly. "
        ))
        prompt = [sys_msg] + state["messages"]
        response = await bot_model.ainvoke(prompt)
        return {"messages": [response]}

    workflow = StateGraph(BotsAgentState)
    
    # Nodes
    workflow.add_node("agent", bot_node)
    workflow.add_node("tools", ToolNode(bot_tools))
    
    # Edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(name="BotsGraph")
