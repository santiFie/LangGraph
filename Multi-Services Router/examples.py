"""
Example usage of the Multi-Services Router API
Shows how to invoke different agents and use various features
"""

import httpx
import json
from typing import Optional, AsyncGenerator


class RouterClient:
    """Simple client for interacting with the Multi-Services Router"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url)
    
    def health_check(self) -> dict:
        """Check router health"""
        response = self.client.get("/health")
        response.raise_for_status()
        return response.json()
    
    def invoke_supervisor(self, user_message: str) -> dict:
        """Invoke the supervisor with a user message"""
        payload = {
            "input": {
                "messages": [{"role": "user", "content": user_message}]
            }
        }
        
        response = self.client.post(
            "/supervisor/invoke",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    
    def stream_supervisor(self, user_message: str) -> httpx.Response:
        """Stream response from supervisor"""
        payload = {
            "input": {
                "messages": [{"role": "user", "content": user_message}]
            }
        }
        
        response = self.client.post(
            "/supervisor/stream",
            json=payload,
            timeout=None
        )
        response.raise_for_status()
        return response


def example_1_health_check():
    """Example 1: Basic health check"""
    print("\n📊 Example 1: Health Check")
    print("-" * 50)
    
    client = RouterClient()
    health = client.health_check()
    
    print(f"Status: {health['status']}")
    print(f"Environment: {health['environment']}")
    print(f"Database: {health['database']}")


def example_2_search_agent():
    """Example 2: Use the search agent"""
    print("\n🔍 Example 2: Search Agent")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "What is the difference between supervised and unsupervised learning?"
    print(f"Query: {query}\n")
    
    result = client.invoke_supervisor(query)
    
    # Extract the response
    messages = result.get("output", {}).get("messages", [])
    if messages:
        last_message = messages[-1]
        if hasattr(last_message, "content"):
            print(f"Response: {last_message.content}")
        else:
            print(f"Response: {last_message}")


def example_3_github_operations():
    """Example 3: GitHub agent operations"""
    print("\n🐙 Example 3: GitHub Operations")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "Create a file named 'test.txt' with content 'Hello from LangGraph' in the repository"
    print(f"Query: {query}\n")
    
    result = client.invoke_supervisor(query)
    messages = result.get("output", {}).get("messages", [])
    
    if messages:
        print("Response:")
        for msg in messages[-3:]:  # Last 3 messages
            role = getattr(msg, "type", "assistant")
            content = getattr(msg, "content", str(msg))
            print(f"  [{role}]: {content}")


def example_4_bot_analysis():
    """Example 4: Bot analysis agent"""
    print("\n🤖 Example 4: Bot Analysis")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "What are the recent bot attack logs?"
    print(f"Query: {query}\n")
    
    result = client.invoke_supervisor(query)
    messages = result.get("output", {}).get("messages", [])
    
    if messages:
        print("Response:")
        for msg in messages[-2:]:  # Last 2 messages
            role = getattr(msg, "type", "assistant")
            content = getattr(msg, "content", str(msg))
            print(f"  [{role}]: {content}")


def example_5_streaming():
    """Example 5: Stream response"""
    print("\n📡 Example 5: Streaming Response")
    print("-" * 50)
    
    client = RouterClient()
    
    query = "Explain neural networks in simple terms"
    print(f"Query: {query}\n")
    
    print("Streaming response:")
    with client.stream_supervisor(query) as response:
        for line in response.iter_lines():
            if line and line.startswith("data: "):
                data = json.loads(line[6:])
                # Process streamed data
                print(f"  {data}")


def example_6_batch_processing():
    """Example 6: Batch processing"""
    print("\n📦 Example 6: Batch Processing")
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


def example_7_async_usage():
    """Example 7: Async usage with httpx"""
    print("\n⚡ Example 7: Async Usage")
    print("-" * 50)
    
    import asyncio
    
    async def fetch_with_async(message: str):
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.post(
                "/supervisor/invoke",
                json={
                    "input": {
                        "messages": [{"role": "user", "content": message}]
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
        health = client.health_check()
        print("✓ Successfully connected to the router!")
        
        # Run examples
        example_1_health_check()
        # example_2_search_agent()
        # example_3_github_operations()
        # example_4_bot_analysis()
        # example_5_streaming()
        # example_6_batch_processing()
        # example_7_async_usage()
        
        print("\n\n✅ Examples completed!")
        print("\nUncomment the examples you want to run in the main() function")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure the API is running:")
        print("  $ python main.py")
        print("Then run this script in another terminal")


if __name__ == "__main__":
    main()
