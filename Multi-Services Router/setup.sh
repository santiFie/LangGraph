#!/bin/bash

# Multi-Services Router Setup Script
# Installs dependencies and configures the application for local development

set -e

echo "🚀 Multi-Services Router - Setup Script"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if Python 3.11+
min_version="3.11"
if ! python3 -c "import sys; exit(0 if sys.version_info >= tuple(map(int, '$min_version'.split('.'))) else 1)"; then
    echo "✗ Python 3.11+ required"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "ℹ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create directories
echo ""
echo "📁 Creating necessary directories..."
mkdir -p "RAG PDFs"
mkdir -p checkpoint_data
mkdir -p logs

# Configure environment
echo ""
echo "⚙️  Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env from template"
    echo "⚠️  Please edit .env with your API keys"
else
    echo "ℹ .env already exists"
fi

# Install Node dependencies for MCP servers (if needed)
if command -v npm &> /dev/null; then
    echo ""
    echo "📦 Installing MCP servers..."
    npm install -g @modelcontextprotocol/server-filesystem
    npm install -g @modelcontextprotocol/server-github
    echo "✓ MCP servers installed"
else
    echo "⚠️  Node.js not found. MCP servers require npm"
    echo "   Install from: https://nodejs.org/"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Add PDF files to 'RAG PDFs' directory"
echo "3. Run: python main.py"
echo ""
echo "For Docker deployment:"
echo "1. Edit .env with your API keys"
echo "2. Run: docker-compose up --build"
echo ""
