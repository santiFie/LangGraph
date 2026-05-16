"""
Configuración centralizada para la aplicación Multi-Services Router
Gestiona variables de entorno y configuración global
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Cargar variables de entorno
load_dotenv()


class Config:
    """Clase principal de configuración"""
    
    # ==================== GENERAL ====================
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # ==================== LLM PROVIDERS ====================
    # Google Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # NVIDIA
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    
    # HuggingFace
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    
    # ==================== SEARCH & RAG ====================
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    TAVILY_MAX_RESULTS: int = 3
    
    # RAG Configuration
    RAG_PDF_PATH: str = os.getenv("RAG_PDF_PATH", "./rag_pdfs")
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    RETRIEVER_K: int = 5
    
    # ==================== LANGCHAIN ====================
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: Optional[str] = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "Multi-Services-Router")
    
    # ==================== MCP SERVERS ====================
    # GitHub MCP
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_PERSONAL_ACCESS_TOKEN: Optional[str] = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    DEFAULT_GITHUB_REPO: str = os.getenv("DEFAULT_GITHUB_REPO", "santiFie/LangGraph")
    
    # Filesystem MCP
    WORKSPACE_PATH: str = os.getenv("WORKSPACE_PATH", "/home/santi/Documentos/LangGraph/")
    
    # Bots MCP
    BOTS_API_URL: str = os.getenv("BOTS_API_URL", "http://localhost:8001")
    BOTS_MCP_URL: str = os.getenv("BOTS_MCP_URL", "http://localhost:8001/sse")
    
    # ==================== DATABASE ====================
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./checkpoint.db")
    CHECKPOINT_DB: str = os.getenv("CHECKPOINT_DB", "checkpoint.db")
    
    # ==================== SERVER ====================
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    SERVER_RELOAD: bool = DEBUG
    
    # ==================== LANGSERVE ====================
    LANGSERVE_ENABLE_DOCS: bool = os.getenv("LANGSERVE_ENABLE_DOCS", "true").lower() == "true"
    LANGSERVE_ENABLE_PLAYGROUND: bool = os.getenv("LANGSERVE_ENABLE_PLAYGROUND", "true").lower() == "true"
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ==================== AGENTS ====================
    SEARCHER_MODEL: str = os.getenv("SEARCHER_MODEL", "llama-3.3-70b-versatile")
    GITHUB_MODEL: str = os.getenv("GITHUB_MODEL", "gemini-3.1-flash-lite-preview")
    SUPERVISOR_MODEL: str = os.getenv("SUPERVISOR_MODEL", "gpt-4")
    
    @classmethod
    def validate(cls) -> bool:
        """Valida que las variables de entorno críticas estén configuradas"""
        required_keys = [
            "GEMINI_API_KEY",
            "GROQ_API_KEY",
            "TAVILY_API_KEY",
        ]
        
        missing = [key for key in required_keys if not getattr(cls, key)]
        
        if missing:
            print(f"⚠️  Advertencia: Variables de entorno faltantes: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def to_dict(cls) -> dict:
        """Retorna configuración como diccionario"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and key.isupper()
        }


# Instancia singleton
config = Config()
