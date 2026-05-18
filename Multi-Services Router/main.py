"""
FastAPI application entry point for the Multi-Services Router.
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, Field

from core.graph import create_supervisor_graph
from core.utils.config import config


logging.basicConfig(level=config.LOG_LEVEL, format=config.LOG_FORMAT)
logger = logging.getLogger(__name__)


class SupervisorConfigurable(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    checkpoint_ns: str = "SupervisorGraph"
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SupervisorRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class BatchRequest(BaseModel):
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


def _is_resource_exhausted_error(exc: Exception) -> bool:
    message = str(exc).upper()
    if "RESOURCE_EXHAUSTED" in message:
        return True

    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True

    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) == 429:
        return True

    response_text = getattr(response, "text", "")
    return isinstance(response_text, str) and "RESOURCE_EXHAUSTED" in response_text.upper()


def _graph_http_exception(exc: Exception) -> HTTPException:
    if _is_resource_exhausted_error(exc):
        return HTTPException(
            status_code=429,
            detail="RESOURCE_EXHAUSTED: quota or rate limit exceeded",
        )

    return HTTPException(status_code=500, detail=str(exc))


def _ensure_message(message: Any) -> BaseMessage:
    if isinstance(message, BaseMessage):
        return message

    if isinstance(message, dict):
        message_type = (message.get("type") or message.get("role") or "human").lower()
        content = message.get("content", "")
        if message_type in {"human", "user"}:
            return HumanMessage(content=content)
        if message_type in {"assistant", "ai"}:
            return AIMessage(content=content)
        if message_type == "system":
            return SystemMessage(content=content)
        if message_type == "tool":
            return ToolMessage(content=content, tool_call_id=message.get("tool_call_id", "tool-call"))

    return HumanMessage(content=str(message))


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]

    if isinstance(value, BaseMessage):
        data = value.model_dump()
        data["type"] = getattr(value, "type", data.get("type", value.__class__.__name__.lower()))
        return _serialize_value(data)

    if hasattr(value, "model_dump"):
        try:
            return _serialize_value(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return _serialize_value(value.dict())
        except Exception:
            pass

    if hasattr(value, "content") and hasattr(value, "type"):
        return _serialize_value(
            {
                "type": getattr(value, "type", value.__class__.__name__.lower()),
                "content": getattr(value, "content", str(value)),
            }
        )

    return str(value)


def _build_graph_input(payload: dict[str, Any]) -> dict[str, Any]:
    input_data = dict(payload.get("input") or {})
    messages = input_data.get("messages", [])
    if messages:
        # Ensure all messages are BaseMessage instances
        input_data["messages"] = [_ensure_message(message) for message in messages]
    return input_data


def _build_graph_config(payload: dict[str, Any], thread_id: Optional[str] = None) -> dict[str, Any]:
    config_data = dict(payload.get("config") or {})
    configurable = dict(config_data.get("configurable") or {})
    if thread_id and "thread_id" not in configurable:
        configurable["thread_id"] = thread_id
    configurable.setdefault("thread_id", str(uuid.uuid4()))
    configurable.setdefault("checkpoint_ns", "SupervisorGraph")
    configurable.setdefault("checkpoint_id", str(uuid.uuid4()))
    config_data["configurable"] = configurable
    return config_data


async def _run_graph(request_payload: dict[str, Any]) -> Any:
    graph = app.state.supervisor_graph
    if graph is None:
        raise RuntimeError("Supervisor graph is not initialized yet")

    graph_input = _build_graph_input(request_payload)
    graph_config = _build_graph_config(request_payload)
    try:
        return await graph.ainvoke(graph_input, config=graph_config)
    except Exception as exc:
        raise _graph_http_exception(exc) from exc


async def _stream_graph(request_payload: dict[str, Any]):
    graph = app.state.supervisor_graph
    if graph is None:
        raise RuntimeError("Supervisor graph is not initialized yet")

    graph_input = _build_graph_input(request_payload)
    graph_config = _build_graph_config(request_payload)

    try:
        async for chunk in graph.astream(graph_input, config=graph_config):
            yield f"data: {json.dumps(_serialize_value(chunk), ensure_ascii=True)}\n\n"
    except Exception as exc:
        if _is_resource_exhausted_error(exc):
            yield f"data: {json.dumps({'error': 'RESOURCE_EXHAUSTED', 'detail': 'quota or rate limit exceeded'}, ensure_ascii=True)}\n\n"
            return
        raise

    yield f"data: {json.dumps({'event': 'done'}, ensure_ascii=True)}\n\n"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Multi-Services Router...")
    checkpoint_db = config.CHECKPOINT_DB
    db_dir = os.path.dirname(checkpoint_db)

    conn: Optional[aiosqlite.Connection] = None
    try:
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        if not os.path.exists(checkpoint_db):
            open(checkpoint_db, "a").close()
            logger.info("Created checkpoint database file: %s", checkpoint_db)

        conn = await aiosqlite.connect(checkpoint_db)
        app.state.checkpoint_conn = conn
        app.state.persistence_saver = AsyncSqliteSaver(conn)
        logger.info("SQLite checkpoint saver ready at %s", checkpoint_db)

        app.state.supervisor_graph = await create_supervisor_graph(app.state.persistence_saver)
        logger.info("Supervisor graph created successfully")

        yield
    except Exception:
        logger.exception("Error during startup")
        raise
    finally:
        if conn is not None:
            await conn.close()


app = FastAPI(
    title="Multi-Services Router",
    description="Intelligent service router with RAG, bot MCP, and GitHub integration",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": config.ENVIRONMENT,
        "database": config.CHECKPOINT_DB,
    }


@app.post("/supervisor/invoke")
async def invoke_supervisor(request: SupervisorRequest):
    try:
        output = await _run_graph(request.model_dump())
    except Exception as exc:
        logger.exception("Supervisor invocation failed")
        raise _graph_http_exception(exc) from exc

    return {"output": _serialize_value(output)}


@app.post("/supervisor/batch")
async def batch_supervisor(request: BatchRequest):
    try:
        results = await asyncio.gather(*[_run_graph({"input": item, "config": request.config}) for item in request.inputs])
    except Exception as exc:
        logger.exception("Supervisor batch failed")
        raise _graph_http_exception(exc) from exc

    return {"output": [_serialize_value(result) for result in results]}


@app.post("/supervisor/stream")
async def stream_supervisor(request: SupervisorRequest):
    return StreamingResponse(
        _stream_graph(request.model_dump()),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=config.SERVER_RELOAD,
        log_level=config.LOG_LEVEL.lower(),
    )
