"""
RAG context retriever for the Planner — dual-index architecture.

Two independent FAISS vector stores are built and queried in parallel:

1. **Agent RAG** (`agent_docs/`)
   One Markdown file per agent, describing *only* its capabilities and
   constraints (no cross-agent workflows).  This lets the Planner know
   *what each agent can do* and which one to pick for a task.

2. **Playbook RAG** (`playbooks/`)
   One Markdown file per workflow/task type (e.g. "upload file to MinIO",
   "DSpace export → MinIO").  These define *how* multi-step, multi-agent
   flows should be structured, including sequencing, prerequisites, and
   critical parameters.

Both stores are cached (built once per process) and queried independently.
Their results are combined into a single ``domain_context`` string that is
injected into the Planner's prompt.

Adding a new agent:  drop a ``<agent_name>.md`` in ``agent_docs/``.
Adding a new workflow: drop a ``<workflow_name>.md`` in ``playbooks/``.
No code changes needed.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Directory paths
_MODULE_DIR = Path(__file__).resolve().parent          # core/utils/
_PROJECT_ROOT = _MODULE_DIR.parent.parent              # Multi-Services Project/
AGENT_DOCS_DIR = _PROJECT_ROOT / "agent_docs"
PLAYBOOKS_DIR  = _PROJECT_ROOT / "playbooks"

# Embedding model (reused by both stores)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Chunking / retrieval config
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100
AGENT_K       = 4   # chunks to retrieve from the agent-docs index per query
PLAYBOOK_K    = 3   # chunks to retrieve from the playbook index per query


# Helpers
def _load_markdown_docs(docs_dir: Path, doc_type: str) -> list[Document]:
    """Load all ``*.md`` files in *docs_dir* and split them into chunks.

    Each chunk gets ``source`` (filename stem) and ``doc_type`` metadata keys.

    Args:
        docs_dir: Directory containing the Markdown files.
        doc_type: Label injected into metadata (``"agent"`` or ``"playbook"``).
    """
    if not docs_dir.exists():
        raise FileNotFoundError(
            f"{doc_type} docs directory not found at: {docs_dir}\n"
            f"Create it and add Markdown files there."
        )

    headers_to_split_on = [
        ("#",   "h1"),
        ("##",  "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    all_docs: list[Document] = []

    for md_file in sorted(docs_dir.glob("*.md")):
        raw_text = md_file.read_text(encoding="utf-8")
        header_splits = md_splitter.split_text(raw_text)
        char_splits   = char_splitter.split_documents(header_splits)

        for doc in char_splits:
            doc.metadata["source"]   = md_file.stem
            doc.metadata["file"]     = md_file.name
            doc.metadata["doc_type"] = doc_type

        all_docs.extend(char_splits)
        logger.debug("Loaded %d chunks from %s (%s)", len(char_splits), md_file.name, doc_type)

    logger.info("Total %s chunks loaded: %d", doc_type, len(all_docs))
    return all_docs


@lru_cache(maxsize=1)
def _get_embeddings() -> HuggingFaceEmbeddings:
    """Build (and cache) the shared embedding model."""
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def _build_agent_vectorstore() -> FAISS:
    """Build and cache the FAISS index for agent capability docs."""
    logger.info("Building agent-docs vector store from: %s", AGENT_DOCS_DIR)
    docs = _load_markdown_docs(AGENT_DOCS_DIR, "agent")
    store = FAISS.from_documents(docs, _get_embeddings())
    logger.info("Agent vector store ready (%d vectors).", store.index.ntotal)
    return store


@lru_cache(maxsize=1)
def _build_playbook_vectorstore() -> FAISS:
    """Build and cache the FAISS index for workflow playbooks."""
    logger.info("Building playbook vector store from: %s", PLAYBOOKS_DIR)
    docs = _load_markdown_docs(PLAYBOOKS_DIR, "playbook")
    store = FAISS.from_documents(docs, _get_embeddings())
    logger.info("Playbook vector store ready (%d vectors).", store.index.ntotal)
    return store


def _format_chunks(docs: list[Document]) -> list[str]:
    """Format retrieved chunks as Markdown sections with source label."""
    sections: list[str] = []
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        header_trail = " > ".join(
            v for k, v in doc.metadata.items()
            if k in ("h1", "h2", "h3") and v
        )
        label = f"[{source}]" + (f" {header_trail}" if header_trail else "")
        sections.append(f"### {label}\n{doc.page_content.strip()}")
    return sections


# Retriever
def retrieve_planner_context(
    query: str,
    agent_k: int = AGENT_K,
    playbook_k: int = PLAYBOOK_K,
) -> str:
    """Return a combined context string for the Planner.

    Queries both the agent-docs and playbook RAG indexes in parallel and
    combines their results into a single formatted string ready to be
    injected into the Planner's ``domain_context`` field.

    Args:
        query:      The raw user request (same string sent to the Planner).
        agent_k:    Number of chunks to retrieve from the agent-docs index.
        playbook_k: Number of chunks to retrieve from the playbook index.

    Returns:
        A formatted Markdown string, or an empty string if both retrievals
        fail (so the planner can still run without context — graceful degradation).
    """
    agent_sections:    list[str] = []
    playbook_sections: list[str] = []
    agent_sources:     set[str]  = set()
    playbook_sources:  set[str]  = set()

    # --- Agent RAG ---
    try:
        agent_store = _build_agent_vectorstore()
        agent_docs  = agent_store.as_retriever(search_kwargs={"k": agent_k}).invoke(query)
        if agent_docs:
            agent_sections = _format_chunks(agent_docs)
            agent_sources  = {d.metadata.get("source", "unknown") for d in agent_docs}
        else:
            logger.warning("No agent-docs context found for query: %s", query[:80])
    except Exception as exc:  # noqa: BLE001
        logger.error("Agent RAG retrieval failed: %s", exc, exc_info=True)

    # --- Playbook RAG ---
    try:
        playbook_store = _build_playbook_vectorstore()
        playbook_docs  = playbook_store.as_retriever(search_kwargs={"k": playbook_k}).invoke(query)
        if playbook_docs:
            playbook_sections = _format_chunks(playbook_docs)
            playbook_sources  = {d.metadata.get("source", "unknown") for d in playbook_docs}
        else:
            logger.warning("No playbook context found for query: %s", query[:80])
    except Exception as exc:  # noqa: BLE001
        logger.error("Playbook RAG retrieval failed: %s", exc, exc_info=True)

    # --- Combine ---
    if not agent_sections and not playbook_sections:
        return ""

    parts: list[str] = ["## Relevant Context (retrieved from knowledge base)\n"]

    if agent_sections:
        agents_mentioned = ", ".join(sorted(agent_sources))
        parts.append(
            f"### 🤖 Agent Capabilities *(agents: {agents_mentioned})*\n\n"
            + "\n\n".join(agent_sections)
        )

    if playbook_sections:
        playbooks_mentioned = ", ".join(sorted(playbook_sources))
        parts.append(
            f"### 📋 Workflow Playbooks *(playbooks: {playbooks_mentioned})*\n\n"
            + "\n\n".join(playbook_sections)
        )

    return "\n\n".join(parts) + "\n"
