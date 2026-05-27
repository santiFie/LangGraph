"""HTTP API tests for the Multi-Services Router."""

import pytest
from fastapi.testclient import TestClient

import main as main_module
from main import app


class DummyGraph:
    async def ainvoke(self, graph_input, config=None):
        message = graph_input["messages"][0]
        return {
            "messages": [
                {
                    "type": "ai",
                    "content": message.content,
                }
            ]
        }


@pytest.fixture()
def mock_supervisor_graph(monkeypatch):
    async def fake_create_supervisor_graph(_persistence_saver):
        return DummyGraph()

    monkeypatch.setattr(main_module, "create_supervisor_graph", fake_create_supervisor_graph)


@pytest.fixture()
def client(mock_supervisor_graph):
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_supervisor_invoke_accepts_bearer_header(client):
    response = client.post(
        "/supervisor/invoke",
        headers={"Authorization": "Bearer secure_token_123"},
        json={"input": {"messages": [{"type": "human", "content": "hola"}]}, "config": {}},
    )

    assert response.status_code == 200
    assert response.json()["output"]["messages"][0]["content"] == "hola"


def test_supervisor_invoke_accepts_invalid_bearer_header(client):
    response = client.post(
        "/supervisor/invoke",
        headers={"Authorization": "Bearer invalid_token_123"},
        json={"input": {"messages": [{"type": "human", "content": "hola"}]}, "config": {}},
    )

    assert response.status_code == 200
    assert response.json()["output"]["messages"][0]["content"] == "hola"


def test_supervisor_invoke_accepts_missing_authorization_header(client):
    response = client.post(
        "/supervisor/invoke",
        json={"input": {"messages": [{"type": "human", "content": "hola"}]}, "config": {}},
    )

    assert response.status_code == 200
    assert response.json()["output"]["messages"][0]["content"] == "hola"