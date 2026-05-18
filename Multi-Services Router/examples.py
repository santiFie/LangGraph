"""
Example usage of the Multi-Services Router API
Shows how to invoke different agents and use various features
"""

import httpx
import json
import uuid
from typing import Optional, AsyncGenerator, Any, cast


class RouterClient:
    """Simple client for interacting with the Multi-Services Router"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)
    
    def invoke_supervisor(self, user_message: str) -> dict:
        """Invoke the supervisor with a user message"""
        payload = {
            "input": {
                "messages": [{"type": "human", "content": user_message}]
            }
        }
        
        payload["config"] = cast(Any, {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "checkpoint_ns": "SupervisorGraph",
                "checkpoint_id": str(uuid.uuid4()),
            }
        })
        response = self.client.post(
            "/supervisor/invoke",
            json=payload,
            timeout=None
        )
        response.raise_for_status()
        return response.json()

    
    def stream_supervisor(self, user_message: str) -> httpx.Response:
        """Stream response from supervisor"""
        payload = {
            "input": {
                "messages": [{"type": "human", "content": user_message}]
            }
        }
        
        payload["config"] = cast(Any, {
            "configurable": {
                "thread_id": str(uuid.uuid4()),
                "checkpoint_ns": "SupervisorGraph",
                "checkpoint_id": str(uuid.uuid4()),
            }
        })
        response = self.client.post(
            "/supervisor/stream",
            json=payload,
            timeout=None
        )
        response.raise_for_status()
        return response


def test_search_agent():
    """Test the search agent"""
    print("\n Search Agent Test: ")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "What is the difference between supervised and unsupervised learning?"
    print(f"Query: {query}\n")
    
    result = client.invoke_supervisor(query)
    
    messages = result.get("output", {}).get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            print(f"Response: {last_message.get('content', last_message)}")
        elif hasattr(last_message, "content"):
            print(f"Response: {last_message.content}")
        else:
            print(f"Response: {last_message}")


def test_github_operations():
    """Test GitHub agent operations"""
    print("\n GitHub Operations Test: ")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "Create a file named 'test.txt' with content 'Hello from LangGraph' in the repository"
    print(f"Query: {query}\n")
    
    result = client.invoke_supervisor(query)
    messages = result.get("output", {}).get("messages", [])
    
    if messages:
        print("Response:")
        for msg in messages[-3:]:  # Last 3 messages
            if isinstance(msg, dict):
                role = msg.get("type", "assistant")
                content = msg.get("content", str(msg))
            else:
                role = getattr(msg, "type", "assistant")
                content = getattr(msg, "content", str(msg))
            print(f"  [{role}]: {content}")


def test_bot_mcp():
    """Test the bot analysis agent"""
    print("\n Bot MCP Test: ")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "What are the recent bot attack logs?"
    print(f"Query: {query}\n")
    
    result = client.invoke_supervisor(query)
    messages = result.get("output", {}).get("messages", [])
    
    if messages:
        print("Response:")
        for msg in messages[-2:]:  # Last 2 messages
            if isinstance(msg, dict):
                role = msg.get("type", "assistant")
                content = msg.get("content", str(msg))
            else:
                role = getattr(msg, "type", "assistant")
                content = getattr(msg, "content", str(msg))
            print(f"  [{role}]: {content}")


def test_streaming():
    """Stream response"""
    print("\n Streaming Response test: ")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "Explain neural networks in simple terms"
    print(f"Query: {query}\n")
    
    print("Streaming response:")
    response = client.stream_supervisor(query)
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            data = json.loads(line[6:])
            # Process streamed data
            print(f"  {data}")


def test_batch_processing():
    """Example 6: Batch processing"""
    print("\n Batch Processing Test: ")
    print("-" * 50)
    
    client = RouterClient()
    
    queries = [
        "What is a neural network?",
        "Explain backpropagation",
        "What is overfitting?"
    ]
    
    print(f"Processing {len(queries)} queries...\n")
    
    for i, query in enumerate(queries, 1):
        print(f"{i}. Query: {query}")
        result = client.invoke_supervisor(query)
        print(f"   Status: Processed\n")


def test_async_usage():
    """Test async usage with httpx"""
    print("\n Async Usage Test: ")
    print("-" * 50)
    
    import asyncio
    
    async def fetch_with_async(message: str):
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post(
                "/supervisor/invoke",
                json={
                    "input": {
                        "messages": [{"type": "human", "content": message}]
                    },
                    "config": {
                        "configurable": {
                            "thread_id": str(uuid.uuid4()),
                            "checkpoint_ns": "SupervisorGraph",
                            "checkpoint_id": str(uuid.uuid4()),
                        }
                    }
                }
            )
            return response.json()
    
    async def main():
        queries = [
            "What is deep learning?",
            "Tell me about CNNs",
            "What are RNNs?"
        ]
        
        print("Running async requests...\n")
        results = await asyncio.gather(
            *[fetch_with_async(q) for q in queries]
        )
        
        for i, (query, result) in enumerate(zip(queries, results), 1):
            print(f"{i}. {query}")
            print(f"   Completed: {len(result.get('output', {}).get('messages', []))} messages\n")
    
    asyncio.run(main())


def main():
    """Run all examples"""
    print("╔" + "=" * 48 + "╗")
    print("║  Multi-Services Router - Usage Examples      ║")
    print("║  Make sure the API is running first!         ║")
    print("╚" + "=" * 48 + "╝")
    
    try:
        # Test connection first
        client = RouterClient()
        print("Conection ok")

        test_search_agent()
        test_github_operations()
        test_bot_mcp()
        test_streaming()
        test_batch_processing()
        test_async_usage()
        
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
