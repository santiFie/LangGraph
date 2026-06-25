import os
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from core.utils.config import config
from core.utils.get_local_model import get_local_model
from core.utils.prompt_loader import load_agent_prompt

DOWNLOADS_DIR = config.DOWNLOADS_DIR
USE_LOCAL_MODEL = False  # Boolean constant to decide which model to use for the MinioAgent.
class MinioAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def _get_model():
    """Returns the appropriate model instance based on the USE_LOCAL_MODEL flag."""
    if USE_LOCAL_MODEL:
        model = await get_local_model()
    else:
        model = ChatOpenAI(
            model=config.MINIO_MODEL,
            api_key=config.OPEN_ROUTER_API_KEY,
            base_url=config.OPEN_ROUTER_BASE_URL,
            temperature=0,
        )
    return model

@tool
def get_host_downloads_dir() -> str:
    """Returns the path to the shared downloads directory on the host machine. This is where the MinIO tools read/write files from."""
    return DOWNLOADS_DIR

async def build_minio_workflow(tools):

    tools.append(get_host_downloads_dir)
    minio_model = await _get_model()
    minio_model = minio_model.bind_tools(tools=tools)  
    #minio_model = get_minio_model_with_tools(tools)

    async def minio_node(state):
        """Node function for Minio operations"""
        messages = state["messages"]

        system_message = SystemMessage(content=load_agent_prompt("minio_agent"))
        
        prompt = [system_message] + messages
        response = await minio_model.ainvoke(prompt)

        return {"messages": [response]}
    
    workflow = StateGraph(MinioAgentState)

    workflow.add_node("minio_agent", minio_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "minio_agent")
    workflow.add_conditional_edges("minio_agent", tools_condition)
    workflow.add_edge("tools", "minio_agent")

    return workflow.compile(name="MinioAgentWorkflow")