"""Authentication tests for the live LangGraph Platform app."""

from __future__ import annotations

import os

import pytest
from langgraph_sdk import get_client

VALID_TOKENS = {
    "secure_token_123": {"id": "user_123", "name": "John Doe", "role": "admin"},
    "secure_token_456": {"id": "user_456", "name": "Jane Smith", "role": "user"},
}

BASE_URL = os.getenv("BASE_URL", "http://localhost:2024")



def _client(token: str | None = None):
    headers = None
    if token is not None:
        headers = {"X-API-Key": token}
    return get_client(url=BASE_URL, headers=headers, api_key=None)


def _status_code(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        return status_code

    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)

    return None


def _detail(exc: Exception) -> str | None:
    detail = getattr(exc, "detail", None)
    if detail:
        return detail

    response = getattr(exc, "response", None)
    if response is not None:
        try:
            payload = response.json()
        except Exception:
            return None

        if isinstance(payload, dict):
            return payload.get("detail")

    return None


@pytest.mark.anyio
async def test_create_thread_with_valid_token():
    """A valid API key should allow thread creation on the live app."""

    client = _client("secure_token_123")
    thread = await client.threads.create()

    assert isinstance(thread, dict)
    assert thread["thread_id"]
    assert thread["status"] == "idle"


@pytest.mark.anyio
async def test_create_thread_with_invalid_token():
    """Invalid tokens should be rejected by the deployed app."""

    client = _client("not-a-valid-token")

    with pytest.raises(Exception) as exc_info:
        await client.threads.create()

    assert _status_code(exc_info.value) == 401
    assert _detail(exc_info.value) == "Invalid token"


@pytest.mark.anyio
async def test_create_thread_without_token():
    """Requests without credentials should be rejected in auth-protected deployments."""

    client = _client()

    with pytest.raises(Exception) as exc_info:
        await client.threads.create()

    assert _status_code(exc_info.value) == 401
    assert _detail(exc_info.value) == "Missing x-api-key header"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])