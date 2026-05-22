"""Vector store abstraction.

A thin interface over the actual backend so the rest of the platform never
imports a specific vendor. `pgvector` is the default (co-located with the
relational data, transactional, zero extra infra); Chroma/Pinecone/Weaviate
implementations can be dropped in behind the same `VectorStore` protocol.

    store = get_vector_store()
    store.upsert(chunks)
    hits = store.similarity_search(query_embedding, owner_id=..., top_k=6)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from apps.core.exceptions import VectorStoreError

logger = logging.getLogger("neuraforge")


@dataclass
class RetrievedChunk:
    chunk_id: str
    content: str
    score: float  # similarity in [0,1]; higher is better
    source_type: str
    source_id: str
    metadata: dict


class VectorStore(Protocol):
    def upsert(self, chunks: list) -> int: ...

    def similarity_search(
        self,
        query_embedding: list[float],
        *,
        owner_id=None,
        team_id=None,
        source_ids: list[str] | None = None,
        top_k: int = 6,
    ) -> list[RetrievedChunk]: ...

    def delete_for_source(self, source_type_id: int, source_id: str) -> int: ...


class PgVectorStore:
    """Default backend backed by the `KnowledgeChunk` table + pgvector."""

    def upsert(self, chunks: list) -> int:
        from apps.ai_engine.models import KnowledgeChunk

        objs = KnowledgeChunk.objects.bulk_create(chunks, batch_size=200)
        return len(objs)

    def similarity_search(
        self,
        query_embedding,
        *,
        owner_id=None,
        team_id=None,
        source_ids=None,
        top_k=6,
    ) -> list[RetrievedChunk]:
        from pgvector.django import CosineDistance

        from apps.ai_engine.models import KnowledgeChunk

        qs = KnowledgeChunk.objects.exclude(embedding=None)
        if owner_id is not None:
            qs = qs.filter(owner_id=owner_id)
        if team_id is not None:
            qs = qs.filter(team_id=team_id)
        if source_ids:
            qs = qs.filter(source_id__in=source_ids)

        # Cosine distance in [0,2]; convert to a 0..1 similarity for callers.
        qs = qs.annotate(distance=CosineDistance("embedding", query_embedding)).order_by(
            "distance"
        )[:top_k]

        return [
            RetrievedChunk(
                chunk_id=str(c.id),
                content=c.content,
                score=round(1.0 - (c.distance / 2.0), 4),
                source_type=c.source_type.model,
                source_id=str(c.source_id),
                metadata=c.metadata,
            )
            for c in qs
        ]

    def delete_for_source(self, source_type_id: int, source_id: str) -> int:
        from apps.ai_engine.models import KnowledgeChunk

        deleted, _ = KnowledgeChunk.objects.filter(
            source_type_id=source_type_id, source_id=source_id
        ).delete()
        return deleted


def get_vector_store() -> VectorStore:
    """Factory: resolve the configured backend."""
    backend = settings.AI_SETTINGS["VECTOR_BACKEND"]
    if backend == "pgvector":
        return PgVectorStore()
    # Extension points — implement and wire as needed.
    if backend in {"chroma", "pinecone", "weaviate"}:
        raise VectorStoreError(
            f"Vector backend '{backend}' is architected but not yet implemented; "
            "use VECTOR_BACKEND=pgvector or add an adapter in vector_store.py."
        )
    raise VectorStoreError(f"Unknown VECTOR_BACKEND '{backend}'")
