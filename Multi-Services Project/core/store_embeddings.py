import asyncio
from functools import partial
from langchain_huggingface import HuggingFaceEmbeddings
from core.utils.config import config

_embeddings = HuggingFaceEmbeddings(
    model_name=config.EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

async def aembed_texts(texts: list[str]) -> list[list[float]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_embeddings.embed_documents, texts))
