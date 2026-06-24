from core.utils.config import config
from langchain_openai import ChatOpenAI


async def get_local_model() -> ChatOpenAI:
    import httpx
    import openai

    orchestrator_api_key = config.ORCHESTRATOR_LOCAL_API_KEY

    if not orchestrator_api_key:
        raise RuntimeError("Missing ORCHESTRATOR_API_KEY_LOCAL environment variable")

    auth_headers = {"X-API-Key": orchestrator_api_key}
    timeout = 60.0

    # HTTP sync client
    sync_httpx_client = httpx.Client(headers=auth_headers, timeout=timeout)

    # HTTP async client
    async_httpx_client = httpx.AsyncClient(headers=auth_headers, timeout=timeout)
    async_openai_client = openai.AsyncOpenAI(
        base_url=config.ORCHESTRATOR_BASE_URL_LOCAL,
        api_key="dummy",
        http_client=async_httpx_client,
    )

    model = ChatOpenAI(
        model="qwen3:30b",
        temperature=0,
        base_url=config.ORCHESTRATOR_BASE_URL_LOCAL,
        api_key="dummy",
        http_client=sync_httpx_client,                  # used by .invoke()
        http_async_client=async_httpx_client,           # used by .ainvoke()
    )

    return model

async def get_local_model_with_tools(tools):
    model = await get_local_model()
    model.bind_tools(tools=tools)

    return model
