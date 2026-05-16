#!/usr/bin/env python3

"""
Multi-Services Router - Quick Start Script
Validates setup and provides usage examples
"""

import sys
import os
from pathlib import Path

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment setup...")
    print("-" * 50)
    
    checks = {
        "Python 3.11+": sys.version_info >= (3, 11),
        ".env file": Path(".env").exists(),
        "RAG PDFs directory": Path("RAG PDFs").exists(),
        "Requirements installed": Path("venv" if os.name != 'nt' else "venv\\Scripts").exists() or check_imports(),
    }
    
    all_good = True
    for check_name, result in checks.items():
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")
        if not result:
            all_good = False
    
    print("-" * 50)
    return all_good


def check_imports():
    """Check if required packages are installed"""
    required = [
        "langchain",
        "langgraph",
        "fastapi",
        "langserve",
    ]
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            return False
    return True


def check_api_keys():
    """Check if API keys are configured"""
    print("\n🔑 Checking API keys...")
    print("-" * 50)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    keys_needed = {
        "GEMINI_API_KEY": "Google Gemini",
        "GROQ_API_KEY": "Groq",
        "TAVILY_API_KEY": "Tavily Search",
        "OPENAI_API_KEY": "OpenAI (optional)",
        "GITHUB_PERSONAL_ACCESS_TOKEN": "GitHub (optional)",
    }
    
    for env_var, service in keys_needed.items():
        value = os.getenv(env_var)
        if value:
            masked = value[:4] + "*" * (len(value) - 8) + value[-4:]
            print(f"✓ {service:30} {masked}")
        else:
            status = "⚠️" if "optional" in service else "✗"
            print(f"{status} {service:30} Missing")


def show_quick_start():
    """Show quick start examples"""
    print("\n\n🚀 Quick Start Guide")
    print("=" * 50)
    
    print("\n1️⃣  Local Development:")
    print("   $ python main.py")
    print("   Visit: http://localhost:8000/docs")
    
    print("\n2️⃣  Docker Deployment:")
    print("   $ docker-compose up --build")
    print("   Visit: http://localhost:8000/docs")
    
    print("\n3️⃣  API Usage Example:")
    print("   $ curl -X POST http://localhost:8000/supervisor/invoke \\")
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"input": {"messages": [{"role": "user", "content": "What is deep learning?"}]}}\'')
    
    print("\n4️⃣  LangGraph Studio:")
    print("   $ langgraph up")
    print("   Visit: http://localhost:8000")
    
    print("\n5️⃣  Run Tests:")
    print("   $ pytest tests/")


def show_troubleshooting():
    """Show common troubleshooting tips"""
    print("\n\n🔧 Troubleshooting")
    print("=" * 50)
    
    print("\n❓ PDF files not loaded in RAG?")
    print("   - Ensure PDFs are in 'RAG PDFs' directory")
    print("   - Supported formats: PDF")
    
    print("\n❓ MCP server connection failed?")
    print("   - Check Bots API is running on port 8001")
    print("   - Verify BOTS_API_URL in .env")
    
    print("\n❓ Database locked error?")
    print("   - Only one process can access checkpoint.db")
    print("   - Restart the application")
    
    print("\n❓ Import errors?")
    print("   - Activate virtual environment: source venv/bin/activate")
    print("   - Reinstall: pip install -r requirements.txt")


def main():
    print("╔" + "=" * 48 + "╗")
    print("║  Multi-Services Router - Setup Validator     ║")
    print("║  Powered by LangGraph & LangServe            ║")
    print("╚" + "=" * 48 + "╝")
    
    if not check_environment():
        print("\n⚠️  Some checks failed. Please fix them before proceeding.")
        sys.exit(1)
    
    check_api_keys()
    show_quick_start()
    show_troubleshooting()
    
    print("\n\n✅ Environment is ready!")
    print("Run 'python main.py' to start the application.")


if __name__ == "__main__":
    main()
