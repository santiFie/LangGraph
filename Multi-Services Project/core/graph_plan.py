"""
Supervisor Graph Coordinator - Plan-and-Execute Pattern.

This module coordinates multiple specialized agents (filesystem, dspace, minio,
bots, searcher, openalex) using a centralized planner and re-planner supervisor.
It builds the StateGraph and orchestrates node execution, state transitions,
RAG context retrieval, human feedback, and episodic memory persistence.
"""

import os
import operator
import asyncio
import logging
from typing import Annotated, Any, TypedDict, List, Tuple, Literal, cast

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from langgraph.store.base import BaseStore

# Agent workflow builders
from core.agent.bots_agent import build_bots_workflow
from core.agent.filesystem_agent import build_filesystem_workflow
from core.agent.researcher_agent import build_searcher_graph
from core.agent.dspace_agent import build_dspace_agent_workflow
from core.agent.minio_agent import build_minio_workflow
from core.agent.openalex_agent import build_openalex_workflow

# Utilities & Configuration
from core.utils.mcp_tools import get_tools
from core.utils.prompt_loader import load_agent_prompt
from core.utils.config import config
from core.utils.rag_context import retrieve_planner_context
from core.utils.local_rag_context import retrieve_planner_context_local

# ==============================================================================
# CONFIGURATION CONSTANTS
# ==============================================================================

# Boolean constant to decide which RAG system to use.
# - True: Uses local RAG API backend via `core/utils/local_rag_context.py`
# - False: Uses local FAISS playbook retriever via `core/utils/rag_context.py`
USE_LOCAL_RAG: bool = True
USE_LOCAL_MODEL: bool = True

DOWNLOADS_DIR = config.DOWNLOADS_DIR

# ==============================================================================
# TYPE DEFINITIONS & SCHEMAS
# ==============================================================================

AgentName = Literal["filesystem", "dspace", "minio", "bots", "searcher", "openalex"]


class PlanStep(BaseModel):
    """Represents a single discrete step in the plan."""
    task: str = Field(
        description="Clear and concise description of the task to be performed in this step."
    )
    assigned_agent: AgentName = Field(
        description="The agent most suitable to execute this task based on their tools."
    )


class PlanExecuteState(TypedDict):
    """State definition for the Plan-and-Execute LangGraph supervisor."""
    input: str
    domain_context: str  # Dynamic context injected from RAG playbooks
    plan: List[PlanStep]
    past_steps: Annotated[List[Tuple[str, str, str]], operator.add]
    response: str
    human_feedback: dict[str, Any]


class Plan(BaseModel):
    """The complete plan structure to be followed by the supervisor."""
    steps: List[PlanStep] = Field(
        description="Discrete steps to follow to achieve the goal. Each step should be a clear and concise task."
    )


# ==============================================================================
# SUPERVISOR GRAPH CREATOR
# ==============================================================================

# TODO: Add structured_output support for the local models
async def _get_model():
    """Returns the appropriate model instance based on the USE_LOCAL_MODEL flag."""
    if USE_LOCAL_MODEL:
        from core.utils.get_local_model import get_local_model
        model = await get_local_model()
    else:
        model = ChatGroq(model=config.SUPERVISOR_MODEL, temperature=0)
    return model

async def create_supervisor_graph(persistence_saver=None):
    """
    Creates the supervisor graph that coordinates the six agents.
    Requires all MCP sessions to be active.
    """
    # 1. Initialize tools and build sub-graphs
    tools = await get_tools()

    searcher_graph = build_searcher_graph()
    filesystem_graph = await cast(Any, build_filesystem_workflow(tools["filesystem"]))
    bots_graph = await build_bots_workflow(tools["bots"])
    dspace_graph = await build_dspace_agent_workflow(tools["dspace"])
    minio_graph = await build_minio_workflow(tools["minio"])
    openalex_graph = await build_openalex_workflow(tools["openalex"])

    planner_llm = ChatGroq(model=config.SUPERVISOR_MODEL, temperature=0)

    # 2. Prompts
    planner_system_prompt = SystemMessage(content=load_agent_prompt("planner_agent"))

    planner_prompt = ChatPromptTemplate.from_messages([
        planner_system_prompt,
        ("user",
         "## User Request\n{input}\n\n"
         "## Workflow Playbooks\n{domain_context}"
        )
    ])

    planner_chain = planner_prompt | planner_llm.with_structured_output(Plan)

    # 3. Graph Node Functions
    
    async def rag_context_node(state: PlanExecuteState, store: BaseStore) -> dict:
        """Retrieves relevant playbooks and episodic memories as context."""
        context = await _retrieve_playbook_context(state["input"])
        context += await _retrieve_episodic_memory(state["input"], store)
        return {"domain_context": context}

    async def _retrieve_playbook_context(query: str) -> str:
        """Retrieve domain playbooks relevant to the user query."""
        if USE_LOCAL_RAG:
            return await retrieve_planner_context_local(query)
        return retrieve_planner_context(query)

    async def _retrieve_episodic_memory(query: str, store: BaseStore) -> str:
        """Retrieve past successful workflows from episodic memory."""
        try:
            memories = await store.asearch(("episodes",), query=query, limit=2)
            if not memories:
                return ""
            return _format_memories(memories)
        except Exception:
            logging.warning("Failed to read episodic memory", exc_info=True)
            return ""

    def _format_memories(memories) -> str:
        """Format episodic memories into a context block for the planner."""
        parts = [
            "\n\n## Experiencias Pasadas (Past Successful Workflows)\n",
            "Usa estos ejemplos previos para saber cómo resolver tareas similares y qué agentes usar:\n",
        ]
        for mem in memories:
            past_steps = mem.value.get("past_steps", [])
            if not past_steps:
                continue
            parts.append(f"- User Input: {mem.value.get('input', '')}\n")
            feedback = mem.value.get("human_feedback")
            if isinstance(feedback, dict) and feedback.get("user_feedback"):
                parts.append(f"  Feedback del usuario: {feedback['user_feedback']}\n")
            parts.append("  Pasos ejecutados:\n")
            for step_info in past_steps:
                parts.append(_format_step(step_info))
            parts.append("\n")
        return "".join(parts)

    def _format_step(step_info: tuple) -> str:
        """Format a single step (task, agent, result)."""
        if len(step_info) == 3:
            step, agent, result = step_info
            return f"    * [{agent}] {step}\n      Resultado: {result}\n"
        if len(step_info) == 2:
            step, result = step_info
            return f"    * [unknown] {step}\n      Resultado: {result}\n"
        return ""

    async def planner_node(state: PlanExecuteState) -> dict:
        """Generates the initial execution plan."""
        plan = await planner_chain.ainvoke({
            "input": state["input"],
            "domain_context": state.get("domain_context") or "",
        })
        return {"plan": plan.steps}
    
    async def replan_node(state: PlanExecuteState) -> dict:
        """
        Evaluates the progress, corrects plans, removes completed tasks,
        and returns the pending tasks. Returns empty steps if goal is achieved.
        """
        previous_plan = state["plan"]
        past_steps = state.get("past_steps", [])

        # Pre-compute pending tasks — tasks not yet present in past_steps
        executed_task_descriptions = {step for step, _, _ in past_steps}
        pending_tasks = [
            step for step in previous_plan
            if step.task not in executed_task_descriptions
        ]

        executed_context = "\n".join(
            [f"- Task: {step} (Agent: {agent})\n  Result: {result}" for step, agent, result in past_steps]
        ) or "(none)"

        pending_context = "\n".join(
            [f"- {step.task} (Assigned to: {step.assigned_agent})" for step in pending_tasks]
        ) or "(none — all tasks have been executed)"

        replan_prompt = f"""
            You are the Re-planner agent for a multi-agent system.

            Original Goal: '{state['input']}'

            ## Already Executed Tasks (DO NOT repeat these):
            {executed_context}

            ## Pending Tasks (not yet executed):
            {pending_context}

            Your job is to decide what still needs to be done.

            STRICT RULES:
            1. NEVER repeat a task that already appears in the "Already Executed" section.
            2. KEEP all tasks listed under "Pending Tasks" unless they were made unnecessary by an executed result.
            3. If an executed task produced an error, add corrective steps BEFORE the remaining pending tasks.
            4. CRITICAL — Goal Completion: If "Pending Tasks" shows "(none — all tasks have been executed)"
            AND none of the executed tasks produced an unrecovered error,
            return an EMPTY list of steps immediately. Do not add any new steps.
            5. NEVER add steps whose sole purpose is to "present", "format", "recopilar", or "display" results.
            Those are handled automatically after the plan ends.

            Output ONLY the list of tasks that still need to be executed (empty list if the goal is complete):
        """

        structured_llm = planner_llm.with_structured_output(Plan)
        new_plan = await structured_llm.ainvoke(replan_prompt)

        return {"plan": new_plan.steps}

    def create_agent_node(agent_graph):
        """
        Factory method that builds a node function for a specific agent graph.
        Injects previous execution history as context for the agent's prompt.
        """
        async def node(state: PlanExecuteState) -> dict:
            if not state.get("plan"):
                return {"past_steps": []}

            current_step = state["plan"][0]
            current_task = current_step.task
            current_agent = current_step.assigned_agent
            
            # Format history context
            context_list = []
            for step, agent, result in state.get("past_steps", []):
                context_list.append(f"Step: {step} (Agent: {agent})\nResult: {result}")
            context = "\n".join(context_list)
            
            agent_prompt = f"Current task to execute: {current_task}\n\nPrevious context and results:\n{context}"
            
            response = await agent_graph.ainvoke({"messages": [("user", agent_prompt)]})
            
            if isinstance(response, dict) and "messages" in response:
                agent_result = response["messages"][-1].content
            else:
                agent_result = str(response)  # Fallback
                
            return {
                "past_steps": [(current_task, current_agent, agent_result)]
            }
            
        return node
    
    def final_answer_node(state: PlanExecuteState) -> dict:
        """Generates the final natural language response for the user."""
        past_steps = state.get("past_steps", [])
        user_input = state["input"]
        
        context = "\n".join([f"Task: {step} (Agent: {agent})\nResult: {result}" for step, agent, result in past_steps])
        
        final_prompt = f"""You are a helpful AI assistant managing a multi-agent system.
        The user originally asked: '{user_input}'
        
        Here is the log of all actions taken by the specialized agents to fulfill this request:
        {context}
        
        Based ONLY on the results above, provide a clear, natural, and concise final response to the user. 
        Explain what was done and provide any final requested information or confirmation."""
        
        final_llm = ChatGroq(model=config.SUPERVISOR_MODEL, temperature=0.3)
        response = final_llm.invoke(final_prompt)
        
        return {"response": response.content}
    
    def route_current_task(state: PlanExecuteState) -> str:
        """Routes execution to the appropriate node based on the current step."""
        if not state.get("plan"):
            return "final_answer_node"

        current_step = state["plan"][0]
        return current_step.assigned_agent
    
    def human_feedback_node(state: PlanExecuteState) -> dict:
        """Interrupts execution to collect human evaluation of the system's output."""
        feedback = interrupt(
            {
                "request": "Por favor, evalua la respuesta",
                "agent_response": state["response"]
            }
        )
        return {"human_feedback": feedback}

    def evaluate_and_save_memory(state: PlanExecuteState, store: BaseStore) -> PlanExecuteState:
        """Persists successful execution paths to episodic long-term memory."""
        feedback = state.get("human_feedback", {})

        if feedback.get("approved") is True:
            # Serialize steps to dicts for safe store JSON storage
            serialized_plan = [
                step.model_dump() if hasattr(step, "model_dump") else step.dict()
                for step in state.get("plan", [])
            ]
            
            data = {
                "input": state["input"],
                "plan": serialized_plan,
                "past_steps": state.get("past_steps", []),
                "response": state["response"],
                "human_feedback": feedback
            }

            store.put(
                namespace=("episodes",),
                key=state["input"],
                value=data
            )
        
        return state
    
    # 4. Build the workflow StateGraph
    workflow = StateGraph(PlanExecuteState)

    # Add Nodes
    workflow.add_node("rag_context", rag_context_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("replanner", replan_node)
    workflow.add_node("final_answer_node", final_answer_node)
    workflow.add_node("searcher", create_agent_node(searcher_graph))
    workflow.add_node("filesystem", create_agent_node(filesystem_graph))
    workflow.add_node("bots", create_agent_node(bots_graph))
    workflow.add_node("dspace", create_agent_node(dspace_graph))
    workflow.add_node("minio", create_agent_node(minio_graph))
    workflow.add_node("openalex", create_agent_node(openalex_graph))
    workflow.add_node("human_feedback", human_feedback_node)
    workflow.add_node("save_memory", evaluate_and_save_memory)

    # Add Edges & Conditional Routing
    workflow.add_edge(START, "rag_context")
    workflow.add_edge("rag_context", "planner")
    
    workflow.add_conditional_edges("planner", route_current_task, {
        "searcher": "searcher",
        "filesystem": "filesystem",
        "bots": "bots",
        "dspace": "dspace",
        "minio": "minio",
        "openalex": "openalex",
        "replanner": "replanner"
    })

    for agent in ["searcher", "filesystem", "bots", "dspace", "minio", "openalex"]:
        workflow.add_edge(agent, "replanner")

    workflow.add_conditional_edges(
        "replanner",
        route_current_task,
        {
            "searcher": "searcher",
            "filesystem": "filesystem",
            "bots": "bots",
            "dspace": "dspace",
            "minio": "minio",
            "openalex": "openalex",
            "final_answer_node": "final_answer_node"
        }
    )

    workflow.add_edge("final_answer_node", "human_feedback")
    workflow.add_edge("human_feedback", "save_memory")
    workflow.add_edge("save_memory", END)

    # Compile the graph with persistence saver if provided
    if persistence_saver is not None:
        return workflow.compile(checkpointer=persistence_saver, name="SupervisorGraph")
    return workflow.compile(name="SupervisorGraph")


# ==============================================================================
# CONVENIENCE EXPORTERS
# ==============================================================================

def get_supervisor_graph(persistence_saver=None):
    """Returns the supervisor graph for synchronous usage, managing event loops."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(create_supervisor_graph(persistence_saver))


def _load_supervisor_graph():
    """Initializes the default global supervisor graph instance."""
    try:
        return get_supervisor_graph(None)
    except Exception as exc:
        raise RuntimeError("Failed to create the supervisor graph", exc)


# Global instance of the supervisor graph
supervisor_graph = _load_supervisor_graph()