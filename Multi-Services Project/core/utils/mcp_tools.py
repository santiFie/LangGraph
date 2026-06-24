# ==============================================================================
# MCP TOOL RETRIEVAL
# ==============================================================================
import os
from typing import Any
from core.utils.config import config
from langchain_mcp_adapters.client import MultiServerMCPClient

DOWNLOADS_DIR = config.DOWNLOADS_DIR

async def get_tools() -> dict[str, list[Any]]:
    """
    Initializes MCP clients and fetches tools for all specialized agents.
    Returns a dictionary mapping agent names to their respective list of tools.
    """
    system_env = dict(os.environ)

    # 1. Bots MCP Client (SSE)
    bots_client = MultiServerMCPClient(
        {
            "BotsAgent": {
                "url": config.BOTS_MCP_URL.replace("mcp", "127.0.0.1"),
                "transport": "sse",
            }
        }
    )

    # 2. Filesystem MCP Client (Stdio)
    filesystem_client = MultiServerMCPClient(
        {
            "filesystem": {
                "command": "mcp-server-filesystem",
                "args": [config.WORKSPACE_PATH],
                "transport": "stdio",
                "env": system_env,
            },
        }
    )

    # 3. DSpace MCP Client (SSE)
    dspace_client = MultiServerMCPClient(
        {
            "DspaceMCP": {
                "url": config.DSPACE_MCP_URL,
                "transport": "sse",
            }
        }
    )

    # 4. MinIO MCP Client (Stdio / Docker)
    minio_client = MultiServerMCPClient(
        {
            "aistor": {
                "command": "docker",
                "args": [
                    "run",
                    "-i",
                    "--rm",
                    "--network=host",
                    "-v", f"{DOWNLOADS_DIR}:/Downloads",
                    "-e", "MINIO_ENDPOINT=localhost:9003",
                    "-e", f"MINIO_ACCESS_KEY={config.MINIO_ROOT_USER}",
                    "-e", f"MINIO_SECRET_KEY={config.MINIO_ROOT_PASSWORD}",
                    "-e", "MINIO_USE_SSL=false",
                    "quay.io/minio/aistor/mcp-server-aistor:latest",
                    "--allowed-directories", "/Downloads",
                    "--allow-write",
                    "--allow-delete",
                    "--allow-admin"
                ],
                "transport": "stdio",
            },
        }
    )

    # 5. OpenAlex MCP Client (Stdio / Docker)
    openalex_client = MultiServerMCPClient(
        {
            "openalex": {
                "command": "docker",
                "args": [
                    "run",
                    "--rm",
                    "-i",
                    "-e", f"OPENALEX_API_KEY={config.OPENALEX_API_KEY}",
                    "-e", f"OPENALEX_EMAIL={config.OPENALEX_EMAIL}",
                    "multi-servicesproject-openalex-mcp",
                ],
                "transport": "stdio",
            }
        }
    )

    # Fetch tools concurrently
    bot_tools = await bots_client.get_tools()
    filesystem_tools = await filesystem_client.get_tools(server_name="filesystem")
    dspace_tools = await dspace_client.get_tools(server_name="DspaceMCP")
    minio_tools = await minio_client.get_tools(server_name="aistor")
    openalex_tools = await openalex_client.get_tools(server_name="openalex")

    return {
        "bots": bot_tools,
        "filesystem": filesystem_tools,
        "dspace": dspace_tools,
        "minio": minio_tools,
        "openalex": openalex_tools
    }