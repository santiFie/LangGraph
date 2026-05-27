"""API tests for the FastAPI router entrypoint."""

import asyncio

import pytest
from fastapi import HTTPException

from main import BatchRequest, SupervisorRequest, _stream_graph, app, batch_supervisor, invoke_supervisor, stream_supervisor


class DummyGraph:
    async def ainvoke(self, graph_input, config=None):
        return {
            "messages": [
                {
                    "type": "ai",
                    "content": graph_input["messages"][0].content,
                }
            ]
        }

    async def astream(self, graph_input, config=None):
        yield {
            "messages": [
                {
                    "type": "ai",
                    "content": graph_input["messages"][0].content,
                }
            ]
        }


class ExhaustedGraph:
    async def ainvoke(self, graph_input, config=None):
        raise RuntimeError("RESOURCE_EXHAUSTED: quota exceeded")

    async def astream(self, graph_input, config=None):
        if False:
            yield None
        raise RuntimeError("RESOURCE_EXHAUSTED: quota exceeded")


@pytest.fixture()
def dummy_graph():
    original_graph = getattr(app.state, "supervisor_graph", None)
    app.state.supervisor_graph = DummyGraph()
    try:
        yield
    finally:
        app.state.supervisor_graph = original_graph


@pytest.mark.usefixtures("dummy_graph")
def test_invoke_supervisor_returns_serialized_output():
    request = SupervisorRequest(input={"messages": [{"type": "human", "content": "hola"}]})
    result = asyncio.run(invoke_supervisor(request))

    assert result == {
        "output": {
            "messages": [
                {
                    "type": "ai",
                    "content": "hola",
                }
            ]
        }
    }


@pytest.mark.usefixtures("dummy_graph")
def test_stream_supervisor_uses_sse_media_type():
    request = SupervisorRequest(input={"messages": [{"type": "human", "content": "hola"}]})
    response = asyncio.run(stream_supervisor(request))

    assert response.media_type == "text/event-stream"


@pytest.mark.usefixtures("dummy_graph")
def test_batch_supervisor_maps_resource_exhausted_to_429():
    original_graph = getattr(app.state, "supervisor_graph", None)
    app.state.supervisor_graph = ExhaustedGraph()
    try:
        request = BatchRequest(
            inputs=[
                {"messages": [{"type": "human", "content": "uno"}]},
                {"messages": [{"type": "human", "content": "dos"}]},
            ]
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(batch_supervisor(request))

        assert exc_info.value.status_code == 429
        assert "RESOURCE_EXHAUSTED" in exc_info.value.detail
    finally:
        app.state.supervisor_graph = original_graph


def test_invoke_supervisor_maps_resource_exhausted_to_429():
    original_graph = getattr(app.state, "supervisor_graph", None)
    app.state.supervisor_graph = ExhaustedGraph()
    try:
        request = SupervisorRequest(input={"messages": [{"type": "human", "content": "hola"}]})
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(invoke_supervisor(request))

        assert exc_info.value.status_code == 429
        assert "RESOURCE_EXHAUSTED" in exc_info.value.detail
    finally:
        app.state.supervisor_graph = original_graph


def test_stream_graph_emits_resource_exhausted_event():
    original_graph = getattr(app.state, "supervisor_graph", None)
    app.state.supervisor_graph = ExhaustedGraph()
    try:
        request_payload = {
            "input": {"messages": [{"type": "human", "content": "hola"}]},
            "config": {},
        }

        async def collect():
            stream = _stream_graph(request_payload)
            return await anext(stream)

        event = asyncio.run(collect())
        assert "RESOURCE_EXHAUSTED" in event
    finally:
        app.state.supervisor_graph = original_graph
