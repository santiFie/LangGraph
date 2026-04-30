# %%
from dotenv import load_dotenv
import os

load_dotenv()

os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("MULTI_SERVICES_ROUTER_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = "Multi-Services Router"
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")
os.environ["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN")
os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
os.environ["NVIDIA_API_KEY"] = os.getenv("NVIDIA_API_KEY")
os.environ["LLAMA_3_3_70B_INSTRUCT_API_KEY"] = os.getenv("LLAMA_3_3_70B_INSTRUCT_API_KEY")


from langchain_openai import ChatOpenAI
from typing import Annotated, TypedDict, Literal
from pydantic import BaseModel, Field
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_groq import ChatGroq
from langgraph.graph.message import add_messages
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from contextlib import AsyncExitStack
from langchain_core.tracers.context import tracing_v2_enabled
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from glob import glob
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.graph import MessagesState
from langgraph_supervisor import create_supervisor


# %% [markdown]
# # Agents

# %% [markdown]
# ## Searcher Agent

# %% [markdown]
# #### RAG

# %%
# Expand glob pattern to actual file paths and load each PDF separately
pdf_paths = glob("./RAG PDFs/*.pdf")
if not pdf_paths:
    raise FileNotFoundError("No PDF files found in ./RAG PDFs/*.pdf")

all_docs = []
for path in pdf_paths:
    loader = PyMuPDFLoader(path)
    all_docs.extend(loader.load())

# Target documents 
target_docs = [doc for doc in all_docs]

# Splitter - Increase chunk_size
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
doc_splits = text_splitter.split_documents(target_docs)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

vectorstore = Chroma.from_documents(
    documents=doc_splits,
    embedding=embeddings,
    collection_name="deep-learning-rag"
)

# Fetch more context chunks
retriever_pdf = vectorstore.as_retriever(search_kwargs={"k": 5})


retriever_tool = create_retriever_tool(
    retriever_pdf,
    "deep-learning-rag-retriever",
    "Search and return information about basic deep learning topics.",
)

retriever_tool.invoke("What is deep learning?")

# %% [markdown]
# #### Search Engine

# %%
tavily_tool = TavilySearchResults(max_results=3)

# %% [markdown]
# ### Create Agent

# %% [markdown]
# #### Generate Query

# %%
from langchain.chat_models import init_chat_model
from langchain_nvidia_ai_endpoints import ChatNVIDIA

response_model = ChatNVIDIA(
    model="meta/llama-3.3-70b-instruct",
    api_key=os.getenv("LLAMA_3_3_70B_INSTRUCT_API_KEY"),
    temperature=0.0,
    top_p=0.3,
    max_completion_tokens=1024,
    name="ResponseLLM"
)

async def generate_query_or_respond(state: MessagesState):
    """
    Call the model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, 
    use tavily searche engine or simply respond to the user.
    """
    system_instruction = SystemMessage(content=(
        "You are an expert in Deep Learning. "
        "If the user greets you or asks a general knowledge question that you can answer without assistance, respond directly. "
        "Only use the 'deep-learning-rag-retriever' tool if the question is technical and specific to neural networks or content from your PDFs."
        "If the answer is not about Deep Learning, look up in the Internet using de tavily tool"
        "If you have the information to anwser, responde to the user"
    ))
    
    prompt = [system_instruction] + state["messages"]  # Include the system instruction in the prompt

    tools = [retriever_tool, tavily_tool]
    response = await (
        response_model
        .bind_tools(tools=tools).ainvoke(prompt)
    )
    return {"messages": [response]}

# %% [markdown]
# #### Test

# %%
input = {"messages": [{"role": "user", "content": "how's the Australian Open last winner?"}]}
response = await generate_query_or_respond(input)
response["messages"][-1].pretty_print()

# %% [markdown]
# #### Grade Documents

# %%
from pydantic import BaseModel, Field
from typing import Literal

GRADE_PROMPT = (
    "You are a grader assessing relevance of a retrieved document to a user question. \n "
    "Here is the retrieved document: \n\n {context} \n\n"
    "Here is the user question: {question} \n"
    "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
    "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
)


class GradeDocuments(BaseModel):
    """Grade documents using a binary score for relevance check."""

    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )

grader_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


async def grade_documents(
    state: MessagesState,
) -> Literal["generate_answer", "rewrite_question"]:
    """Determine whether the retrieved documents are relevant to the question."""
    question = state["messages"][0].content # The first message is the user's question
    context = state["messages"][-1].content # The last message is the retrieved document (context)

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = await (
        grader_model
        .with_structured_output(GradeDocuments).ainvoke(
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score

    if score == "yes":
        return "generate_answer"
    else:
        return "rewrite_question"

# %% [markdown]
# #### Rewrite Question

# %%
REWRITE_PROMPT = (
    "Look at the input and try to reason about the underlying semantic intent / meaning.\n"
    "Here is the initial question:"
    "\n ------- \n"
    "{question}"
    "\n ------- \n"
    "Formulate an improved question:"
)


async def rewrite_question(state: MessagesState):
    """Rewrite the original user question."""
    messages = state["messages"]
    question = messages[0].content
    prompt = REWRITE_PROMPT.format(question=question)
    response = await response_model.ainvoke([{"role": "user", "content": prompt}])
    return {"messages": [{"role": "user", "content": response.content}]}

# %% [markdown]
# #### Generate an answer

# %%
GENERATE_PROMPT = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer the question. "
    "If you don't know the answer, just say that you don't know. "
    "Use three sentences maximum and keep the answer concise.\n"
    "Question: {question} \n"
    "Context: {context}"
)


async def generate_answer(state: MessagesState):
    """Generate an answer."""
    question = state["messages"][0].content
    context = state["messages"][-1].content
    prompt = GENERATE_PROMPT.format(question=question, context=context)
    response = await response_model.ainvoke([{"role": "user", "content": prompt}])
    return {"messages": [response]}

# %% [markdown]
# ### Searcher Subgraph

# %%
def build_searcher_graph(): # -> CompiledGraph
    """Sin MCP: puede compilarse en cualquier momento."""
    
    # async def generate_query_or_respond(state: MessagesState):
    #     sys_msg = SystemMessage(content="You're an expert in Deep Learning...")
    #     response = await response_model.bind_tools([retriever_tool]).ainvoke(
    #         [sys_msg] + state["messages"]
    #     )
    #     return {"messages": [response]}

    workflow = StateGraph(MessagesState)
    workflow.add_node(generate_query_or_respond)
    workflow.add_node("retrieve", ToolNode([retriever_tool, tavily_tool]))
    workflow.add_node(generate_answer)
    workflow.add_node("rewrite_question", rewrite_question)

    # Decide whether to retrieve
    workflow.add_conditional_edges(
        "generate_query_or_respond",
        # Assess LLM decision (call `retriever_tool` tool or respond to the user)
        tools_condition,
        {
            # Translate the condition outputs to nodes in our graph
            "tools": "retrieve",
            END: END,
        },
    )

    # Edges taken after the `action` node is called.
    workflow.add_conditional_edges(
        "retrieve",
        # Assess agent decision
        grade_documents,
    )
    
    workflow.add_edge("generate_answer", END)
    workflow.add_edge("rewrite_question", "generate_query_or_respond")  
    
    return workflow.compile()

# %% [markdown]
# ## Bots Agent

# %%
# Mantenemos el cliente fuera
bots_client = MultiServerMCPClient(
    {
        "BotsAgent": {
            "url": "http://localhost:8001/sse",
            "transport": "sse"
        }
    }
)

def build_bots_workflow(bot_tools):
    bot_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0).bind_tools(tools=bot_tools)

    async def bot_node(state: MessagesState):
        sys_msg = SystemMessage(content=(
            "You are an assistant that can call tools related to Bots to assist users. "
            "Given a user question, decide which tool to call and with what arguments. "
            "If the question is not related to any tool, respond directly to the user. "
            "Dont report any IP if the user asks about it."
            "If you have the information to answer the user's question without calling a tool, respond directly to the user. "
        ))
        prompt = [sys_msg] + state["messages"]
        response = await bot_model.ainvoke(prompt)
        return {"messages": [response]}

    workflow = StateGraph(MessagesState)
    workflow.add_node("bot_agent", bot_node)
    workflow.add_node("tools", ToolNode(bot_tools))
    
    workflow.add_edge(START, "bot_agent")
    workflow.add_conditional_edges("bot_agent", tools_condition)
    workflow.add_edge("tools", "bot_agent")
    
    return workflow.compile()


# %% [markdown]
# #### Test

# %%
# La función de ejecución maneja el ciclo de vida de los recursos
async def run_bots_orchestrator(inputs):
    # Open the connection to MCP and load tools
    async with AsyncExitStack() as stack:
        session = await stack.enter_async_context(bots_client.session("BotsAgent"))
        bot_tools = await load_mcp_tools(session)
        
        # Build the workflow graph with the loaded tools
        bots_graph = build_bots_workflow(bot_tools)
        
        # Execute the graph while the connection is still alive
        result = await bots_graph.ainvoke(inputs)
        
        for msg in result["messages"]:
            msg.pretty_print()

await run_bots_orchestrator({"messages": [{"role": "user", "content": "Exists the IP 192.168.1.1?"}]})

# %% [markdown]
# ## Github Agent

# %%
import os

# This avoids system's "ammnestia"
system_env = dict(os.environ)

# Merge system environment with GitHub token for the GitHub server
github_env = {**system_env, "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")}

path = "/home/santi/Documentos/LangGraph/Multi-Services Router/"

# MCP Client Configuration
client = MultiServerMCPClient(
    {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", path],
            "transport": "stdio",
            "env": system_env # Optional
        },
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": github_env, # Merged environment with GitHub token
            "transport": "stdio",
        }
    }
)

# %%
import warnings
warnings.filterwarnings("ignore", message=".*is not supported in schema.*")

async def build_github_workflow(tools):
    github_model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0).bind_tools(tools=tools)

    async def github_node(state: MessagesState):
        sys_msg = SystemMessage(content=(
            "You are an assistant that can call tools related to GitHub to assist users. "
            f"You have access to the flilesystem tool in the path {path}."
            "Given a user question, decide which tool to call and with what arguments. "
            "If the question is not related to any tool, respond directly to the user. "
            "If you have the information to answer the user's question without calling a tool, respond directly to the user. "
        ))
        prompt = [sys_msg] + state["messages"]
        response = await github_model.ainvoke(prompt)
        return {"messages": [response]}
    
    workflow = StateGraph(MessagesState)
    workflow.add_node("github_agent", github_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_edge(START, "github_agent")
    workflow.add_conditional_edges("github_agent", tools_condition) # Check if the agent decided to call a tool
    workflow.add_edge("tools", "github_agent")

    return workflow.compile()

# %% [markdown]
# #### Test

# %%
async def create_():
    async with AsyncExitStack() as stack:
        # Connect to both servers
        github_session = await stack.enter_async_context(client.session("github"))
        filesystem_session = await stack.enter_async_context(client.session("filesystem"))

        # Load tools from both sessions
        github_tools = await load_mcp_tools(github_session)
        filesystem_tools = await load_mcp_tools(filesystem_session)

        # Combine tools into a single list
        all_tools = github_tools + filesystem_tools

        # Define the workflow with the combined tools
        workflow = await build_github_workflow(all_tools)

        # Example input to the workflow
        input = {"messages": [HumanMessage(content="Can you show me the contents of the file 'Untitled-1.py' in the filesystem?")]}

        # Execute the workflow
        result = await workflow.ainvoke(input)

        for msg in result["messages"]:
            msg.pretty_print()

await create_()

# %% [markdown]
# # Supervisor

# %% [markdown]
# ## Create Supervisor

# %%
supervisor_model = ChatOpenAI(
                model="z-ai/glm-5.1",
                api_key=os.getenv("NVIDIA_API_KEY"),
                base_url="https://integrate.api.nvidia.com/v1", # NVIDIA's API URL
                temperature=0.0,
            )

# %% [markdown]
# ## Graph

# %%

# 1) Compile your subgraphs (make sure these builders exist in earlier cells)
# - searcher_graph: RAG + search tools
# - bots_graph: MCP Bots agent
# - github_graph: MCP GitHub + filesystem agent

async def main(user_input: str):

    async with AsyncExitStack() as stack:

        # 1) Open all the sessions
        bots_session = await stack.enter_async_context(bots_client.session("BotsAgent"))
        github_session = await stack.enter_async_context(client.session("github"))
        filesystem_session = await stack.enter_async_context(client.session("filesystem"))

        # 2) Load tools for each subgraph
        bot_tools = await load_mcp_tools(bots_session)
        github_tools = await load_mcp_tools(github_session)
        filesystem_tools = await load_mcp_tools(filesystem_session)

        # 3) Build/compile subgraphs with their respective tools
        searcher_graph = build_searcher_graph()  # Already compiled in the function
        bots_graph = build_bots_workflow(bot_tools)  # Already compiled in the function
        github_graph = await build_github_workflow(github_tools + filesystem_tools)  # Already compiled in the function

        # 4) Build the supervisor graph with the compiled subgraphs
        supervisor_graph = create_supervisor(
            agents=[searcher_graph, bots_graph, github_graph],
            supervisor_model=supervisor_model,
            prompt=(
                "You are a supervisor that routes tasks to specialized subgraphs: "
                "- 'searcher' for answering questions using retrieved documents about deep learning or searching in the internet, "
                "- 'bots' for answering questions related to bots attacks logs, "
                "- 'github' for answering questions related to GitHub repositories and filesystem operations. "
            )
        ).compile()

        # Execute (all MCP sessions will remain open during the entire execution)
        result = await supervisor_graph.ainvoke({"messages": [HumanMessage(content=user_input)]})

        for msg in result["messages"]:
            msg.pretty_print()

await main("Who won the Australian Open last year?")


