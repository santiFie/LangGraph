from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from core.utils.config import config

DOWNLOADS_DIR = config.DOWNLOADS_DIR

class MinioAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def build_minio_workflow(tools):

    minio_model = ChatGroq(model=config.MINIO_MODEL, temperature=0).bind_tools(tools=tools)

    async def minio_node(state):
        """Node function for Minio operations"""
        messages = state["messages"]

        system_message = SystemMessage(content=f"""
        You are the Storage Management Agent for the service orchestrator. Your primary responsibility is to manage files and objects using the provided MinIO tools.

        CRITICAL INSTRUCTIONS:
        1. Tool Usage: Always use the appropriate MinIO tool to list, read, upload, update, or delete files based on the orchestrator's needs. Do not guess file locations or structures.
        2. Precision: When retrieving or saving data, ensure the bucket names and object paths (keys) are correct.
        3. Data Governance: Treat all files as critical system data. Confirm successful operations before proceeding to the next node in the graph.
        4. Output Format: Always provide a clear summary of the action taken (e.g., "Successfully uploaded 'report.csv' to bucket 'analytics'"). If an operation fails, return the exact error message so the orchestrator can handle the exception.
        5. File Handling: The tools you use run inside a Docker container. Inside this container, the shared staging directory is mounted EXACTLY at the path '/Downloads'. When a tool asks for a file path, you MUST use '/Downloads/filename' (e.g., '/Downloads/.gitignore'). DO NOT use host paths or invent directories like /shared/.
        Context: You operate within an agentic graph workflow. Act efficiently and only invoke tools when strictly necessary to fulfill the requested task.
        """)
        
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