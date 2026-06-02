import httpx
from mcp.server.fastmcp import FastMCP
import os

# Create an MCP server
mcp = FastMCP("Bots MCP Server", host="0.0.0.0", port=8001)

API_URL = os.environ.get("API_URL", "http://api:8000")

@mcp.tool()
async def get_all_bots() -> str:
    """Get all bot records from the database."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/bots/")
        response.raise_for_status()
        return response.text

@mcp.tool()
async def get_bot_by_ip(ip: str) -> str:
    """Get a bot record by IP address."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/bots/{ip}")
        if response.status_code == 404:
            return f"Bot with IP {ip} not found."
        response.raise_for_status()
        return response.text

@mcp.tool()
async def report_bot(ip: str) -> str:
    """Report an attack from a bot IP. Increments attacks or adds it to DB."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/bots/report", json={"ip": ip})
        response.raise_for_status()
        return response.text

if __name__ == "__main__":
    # Alternatively, stdio can be used.
    mcp.run("sse")
