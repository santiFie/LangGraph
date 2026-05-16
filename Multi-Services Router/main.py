"""
LangServe Application Entry Point
Multi-Services Router with LangServe and LangGraph Studio Support
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from fastapi import FastAPI
from langserve import add_routes
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from core.graph import create_supervisor_graph
from core.utils.config import config

# Setup logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Global state
persistence_saver: Optional[AsyncSqliteSaver] = None
supervisor_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager
    Handles startup and shutdown of the application
    """
    global persistence_saver, supervisor_graph
    
    # Startup
    logger.info("Starting Multi-Services Router...")
    
    try:
        
        # Ensure checkpoint database directory and file exist
        checkpoint_db = config.CHECKPOINT_DB
        db_dir = os.path.dirname(checkpoint_db)
        
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Create empty checkpoint.db file if it doesn't exist
        if not os.path.exists(checkpoint_db):
            open(checkpoint_db, 'a').close()
            logger.info(f"Created checkpoint database file: {checkpoint_db}")
        
        # Initialize persistence layer
        logger.info(f"Initialized SQLite checkpoint database: {config.CHECKPOINT_DB}")
        conn = await aiosqlite.connect(config.CHECKPOINT_DB)
        persistence_saver = AsyncSqliteSaver(conn)

        # Create supervisor graph
        supervisor_graph = await create_supervisor_graph(persistence_saver)
        logger.info("Supervisor graph created successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


# Create FastAPI app with lifespan
app = FastAPI(
    title="Multi-Services Router",
    description="Intelligent service router with RAG, bot analysis, and GitHub integration",
    version="1.0.0",
    lifespan=lifespan
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": config.ENVIRONMENT,
        "database": config.CHECKPOINT_DB,
    }


# Add routes
# This will be available at /supervisor/invoke, /supervisor/stream, etc.
if supervisor_graph:
    add_routes(
        app,
        supervisor_graph,
        path="/supervisor",
        enabled_endpoints=["invoke", "batch", "stream", "stream_log"] if config.LANGSERVE_ENABLE_DOCS else [],
    )
    logger.info("Added supervisor graph routes at /supervisor")


# Optional: Add playground
if config.LANGSERVE_ENABLE_PLAYGROUND:
    logger.info("LangServe playground enabled at /supervisor/playground")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=config.SERVER_RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )
