"""
GitHub Agent: Agent for GitHub and filesystem operations
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


class GithubState(TypedDict):
    """State for the GitHub agent"""
    messages: Annotated[list[BaseMessage], add_messages]
    commit_message: str


async def build_github_workflow(tools):
    """
    Builds the GitHub agent graph
    Supports interrupts for commits requiring confirmation
    
    Args:
        tools: List of tools loaded from MCP (github + filesystem)
        
    Returns:
        Compiled GitHub agent graph
    """
    github_model = ChatGoogleGenerativeAI(
        model=config.GITHUB_MODEL,
        temperature=0
    ).bind_tools(tools=tools)

    async def github_agent_node(state: GithubState):
        """Agent node that handles GitHub operations"""
        
        WORKSPACE_PATH = config.WORKSPACE_PATH
        DEFAULT_REPO = config.DEFAULT_GITHUB_REPO
        
        sys_msg = f"""# ROLE
        You are a Senior Platform Engineer specialist in GitHub and filesystem operations.

        # CONTEXT
        - **Root Path:** {WORKSPACE_PATH}
        - **Primary Repository:** {DEFAULT_REPO}
        - **Shared Downloads Directory:** {config.DOWNLOADS_DIR}

        # OPERATIONAL GUIDELINES
        1. **Tool Selection:** - Use `filesystem` tools for local operations
        - Use `github` tools ONLY for remote repository interactions
        2. **Path Resolution:** If only a filename is provided, use directory listing tools.
        3. **Commit Messages:** NEVER generate, guess, or placeholder a commit message.

        # MULTI-AGENT PIPELINE CONSTRAINTS (CRITICAL)
        - You work in a pipeline managed by a Supervisor. 
        - If the task mentions uploading to MinIO, DSpace, or other systems outside your scope, DO NOT TRY TO INTERACT WITH THEM.
        - Your ONLY job in those cases is to COPY or PREPARE the requested file into the shared directory: {config.DOWNLOADS_DIR}.
        - Once you have successfully copied the file to {config.DOWNLOADS_DIR}, respond CONFIRMING only that the file is ready in that directory. Do not say you cannot help with MinIO; just say: "File [name] has been successfully copied to the shared downloads directory."
        """
        prompt = [SystemMessage(content=sys_msg)] + state["messages"]
        
        if state.get("commit_message"):
            prompt.append(
                SystemMessage(
                    content=f"User provided this commit message: {state['commit_message']}"
                )
            )
        
        response = await github_model.ainvoke(prompt)

        # Normalizar respuesta a un objeto de mensaje válido
        if isinstance(response, dict):
            content = response.get("content") or response.get("text") or str(response)
            response_msg = AIMessage(content=content)
        elif isinstance(response, BaseMessage):
            response_msg = response
        else:
            response_msg = AIMessage(content=str(response))

        return {"messages": [response_msg]}
    
    def should_continue(state: GithubState) -> Literal["human_approval", "tools", "END"]:
        """Determine if it needs confirmation, tools, or ends"""
        last_message = state["messages"][-1]
        
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "END"
        
        # Check if there's a file creation without message
        for call in last_message.tool_calls:
            if call.get("name") == "create_or_update_file":
                if not call.get("args", {}).get("message"):
                    return "human_approval"
        
        return "tools"
    
    def human_approval_node(state: GithubState):
        """Node that asks for commit confirmation"""
        return {
            "messages": [
                HumanMessage(
                    content="A commit message is required. Please provide one using the input."
                )
            ]
        }
    
    workflow = StateGraph(GithubState)
    
    # Nodes
    workflow.add_node("agent", github_agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("human_approval", human_approval_node)
    
    # Edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "human_approval": "human_approval",
            "tools": "tools",
            "END": END
        }
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("human_approval", "agent")
    
    return workflow.compile(name="GithubGraph")
