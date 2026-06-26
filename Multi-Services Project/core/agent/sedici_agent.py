"""
Sedici Subgraph Supervisor: Hierarchical orchestrator for SEDICI repository domain.
Coordinates between DatabaseAgent (PostgreSQL SQL) and DSpaceAgent (REST API).
"""

import sys
import os
from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from core.utils.config import config
from core.utils.prompt_loader import load_agent_prompt
from core.agent.dspace_agent import build_dspace_agent_workflow
from core.agent.database_agent import build_database_workflow

USE_LOCAL_MODEL = False


class SediciRoute(BaseModel):
    """Router decision for SEDICI subgraph execution."""
    reasoning: str = Field(description="The reasoning process that led to the decision.")
    target: Literal["database", "dspace", "finish"] = Field(
        description="""Target agent to handle the task.
            - Select 'finish' if the provided context or conversation history already contains the complete answer to the user's current task.
            - Select 'database' if the task requires SQL queries or relational table lookups.
            - Select 'dspace' if the task requires DSpace API operations or bitstream management."""
    )


class SediciAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    route: str
    reasoning: str


async def _get_model():
    if USE_LOCAL_MODEL:
        from core.utils.get_local_model import get_local_model
        model = await get_local_model()
    else:
        model = ChatOpenAI(
            model=config.SEDICI_MODEL,
            api_key=config.OPEN_ROUTER_API_KEY,
            base_url=config.OPEN_ROUTER_BASE_URL,
            temperature=0,
        )
    return model


async def build_sedici_agent_workflow(dspace_tools, database_tools):
    """Builds and compiles the Sedici subgraph workflow."""
    dspace_graph = await build_dspace_agent_workflow(dspace_tools)
    database_graph = await build_database_workflow(database_tools)

    async def router_node(state: SediciAgentState) -> dict:
        sys_msg_content = load_agent_prompt("sedici_agent")
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_msg_content),
            ("placeholder", "{messages}")
        ])

        model = await _get_model()
        structured_model = model.with_structured_output(SediciRoute)
        chain = prompt | structured_model
        
        response = await chain.ainvoke({"messages": state["messages"]})

        route_val = response.target if response else "finish"
        return {"route": route_val, "reasoning": response.reasoning}

    async def run_database_node(state: SediciAgentState) -> dict:
        result = await database_graph.ainvoke({"messages": state["messages"]})
        return {"messages": [result["messages"][-1]]}

    async def run_dspace_node(state: SediciAgentState) -> dict:
        result = await dspace_graph.ainvoke({"messages": state["messages"]})
        return {"messages": [result["messages"][-1]]}

    def route_condition(state: SediciAgentState) -> str:
        return state.get("route", "finish")

    workflow = StateGraph(SediciAgentState)
    workflow.add_node("router", router_node)
    workflow.add_node("database", run_database_node)
    workflow.add_node("dspace", run_dspace_node)

    workflow.add_edge(START, "router")
    workflow.add_conditional_edges("router", route_condition, {
        "database": "database",
        "dspace": "dspace",
        "finish": END
    })
    workflow.add_edge("database", "router")
    workflow.add_edge("dspace", "router")

    return workflow.compile(name="SediciGraph")
