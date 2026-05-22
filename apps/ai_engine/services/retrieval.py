"""Embedding-based retrieval over the vector store (the 'R' in RAG)."""
from __future__ import annotations

from django.conf import settings

from .llm import embed_query
from .vector_store import RetrievedChunk, get_vector_store

AI = settings.AI_SETTINGS


def retrieve(
    query: str,
    *,
    owner_id=None,
    team_id=None,
    source_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Embed the query and return the most relevant chunks, tenant-scoped."""
    store = get_vector_store()
    vector = embed_query(query)
    return store.similarity_search(
        vector,
        owner_id=owner_id,
        team_id=team_id,
        source_ids=source_ids,
        top_k=top_k or AI["RETRIEVAL_TOP_K"],
    )
