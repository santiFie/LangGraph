"""Unit tests for the graph builders in Multi-Services Router."""

import asyncio
from types import SimpleNamespace

import pytest

from core.utils.config import config


class DummyModel:
    """Minimal stand-in for LangChain chat models used by the graphs."""

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.bound_tools = []

    def bind_tools(self, tools):
        self.bound_tools = list(tools)
        return self

    def with_structured_output(self, schema):
        self.structured_schema = schema
        return self

    async def ainvoke(self, prompt):
        return SimpleNamespace(score="yes", critique="", tool_calls=[], content="ok")


class DummyCompiledGraph:
    """Small object that mimics a compiled LangGraph."""

    def __init__(self, name):
        self.name = name

    def invoke(self, *args, **kwargs):
        return {"status": "ok"}

    async def ainvoke(self, *args, **kwargs):
        return {"status": "ok"}


class DummySupervisorBuilder:
    """Captures how the supervisor is assembled before compile()."""

    def __init__(self):
        self.calls = []
        self.last_compile = None

    def __call__(self, model, agents, prompt):
        self.calls.append({
            "model": model,
            "agents": agents,
            "prompt": prompt,
        })
        return self

    def compile(self, name, checkpointer):
        self.last_compile = {
            "name": name,
            "checkpointer": checkpointer,
        }
        return DummyCompiledGraph(name)


class FakeSession:
    def __init__(self, name):
        self.name = name

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeMCPClient:
    def __init__(self, *_args, **_kwargs):
        self.sessions = []

    def session(self, name):
        self.sessions.append(name)
        return FakeSession(name)


def retriever_tool():
    """Stub retriever tool used by ToolNode during tests."""
    return "retriever"


def tavily_tool():
    """Stub Tavily tool used by ToolNode during tests."""
    return "tavily"


class TestConfiguration:
    def test_config_loaded(self):
        assert config is not None

    def test_config_environment(self):
        assert config.ENVIRONMENT in ["development", "production", "staging"]

    def test_config_paths(self):
        assert config.WORKSPACE_PATH is not None
        assert config.RAG_PDF_PATH is not None

    def test_config_to_dict(self):
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert len(config_dict) > 0


def test_build_searcher_graph(monkeypatch):
    from core.agent import researcher

    monkeypatch.setattr(researcher, "generate_retriever", lambda: retriever_tool)
    monkeypatch.setattr(researcher, "generate_tavily", lambda: tavily_tool)
    monkeypatch.setattr(researcher, "ChatGroq", DummyModel)

    graph = researcher.build_searcher_graph()

    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")


def test_build_bots_workflow(monkeypatch):
    from core.agent import bots_agent

    monkeypatch.setattr(bots_agent, "ChatGroq", DummyModel)

    graph = bots_agent.build_bots_workflow([])

    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")


def test_build_github_workflow(monkeypatch):
    from core.agent import github_agent

    monkeypatch.setattr(github_agent, "ChatGoogleGenerativeAI", DummyModel)

    graph = asyncio.run(github_agent.build_github_workflow([]))

    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")


def test_create_supervisor_graph(monkeypatch):
    from core import graph as graph_module

    supervisor_builder = DummySupervisorBuilder()

    monkeypatch.setattr(graph_module, "MultiServerMCPClient", FakeMCPClient)

    async def fake_load_mcp_tools(session):
        return [f"tool-for-{session.name}"]

    monkeypatch.setattr(graph_module, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(graph_module, "ChatOpenAI", DummyModel)
    monkeypatch.setattr(graph_module, "create_supervisor", supervisor_builder)
    monkeypatch.setattr(graph_module, "build_searcher_graph", lambda: SimpleNamespace(name="searcher"))
    monkeypatch.setattr(graph_module, "build_bots_workflow", lambda tools: SimpleNamespace(name="bots", tools=tools))

    async def fake_build_github_workflow(tools):
        return SimpleNamespace(name="github", tools=tools)

    monkeypatch.setattr(graph_module, "build_github_workflow", fake_build_github_workflow)

    graph = asyncio.run(graph_module.create_supervisor_graph(persistence_saver=SimpleNamespace(name="checkpointer")))

    assert graph is not None
    assert graph.name == "SupervisorGraph"
    assert supervisor_builder.calls
    assert supervisor_builder.calls[0]["agents"] == [
        SimpleNamespace(name="searcher"),
        SimpleNamespace(name="bots", tools=["tool-for-BotsAgent"]),
        SimpleNamespace(name="github", tools=["tool-for-github", "tool-for-filesystem"]),
    ]
    assert supervisor_builder.last_compile == {
        "name": "SupervisorGraph",
        "checkpointer": SimpleNamespace(name="checkpointer"),
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
