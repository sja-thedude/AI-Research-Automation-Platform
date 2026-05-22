"""Central LLM/embedding client construction.

Everything goes through here so the provider, model and retry policy are
configured in one place. Swapping OpenAI for Azure/Anthropic/local means
editing only this module.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("neuraforge")
AI = settings.AI_SETTINGS


@lru_cache(maxsize=4)
def get_chat_model(model: str | None = None, temperature: float | None = None):
    """Return a configured LangChain chat model (cached per config)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=AI["OPENAI_API_KEY"],
        model=model or AI["CHAT_MODEL"],
        temperature=AI["TEMPERATURE"] if temperature is None else temperature,
        max_tokens=AI["MAX_TOKENS"],
        timeout=60,
        max_retries=2,
    )


@lru_cache(maxsize=1)
def get_embeddings():
    """Return the configured LangChain embeddings client (cached)."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        api_key=AI["OPENAI_API_KEY"],
        model=AI["EMBEDDING_MODEL"],
        dimensions=AI["EMBEDDING_DIM"],
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with exponential-backoff retry."""
    if not texts:
        return []
    return get_embeddings().embed_documents(texts)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def embed_query(text: str) -> list[float]:
    return get_embeddings().embed_query(text)
