"""Chunk + embed a source object into the vector store.

Used by document indexing and note indexing alike. Idempotent: existing chunks
for the source are cleared before re-ingesting.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from .llm import embed_texts
from .vector_store import get_vector_store

logger = logging.getLogger("neuraforge")
AI = settings.AI_SETTINGS


def _split(text: str) -> list[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=AI["CHUNK_SIZE"],
        chunk_overlap=AI["CHUNK_OVERLAP"],
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [c for c in splitter.split_text(text or "") if c.strip()]


def ingest_source(source_obj, text: str, *, extra_metadata: dict | None = None) -> int:
    """Embed `text` and store chunks linked to `source_obj`.

    Returns the number of chunks written. Scopes chunks to the source's
    owner/team so retrieval stays tenant-isolated.
    """
    from apps.ai_engine.models import KnowledgeChunk

    store = get_vector_store()
    ct = ContentType.objects.get_for_model(source_obj.__class__)

    # Idempotency: wipe prior chunks for this source.
    store.delete_for_source(ct.id, str(source_obj.pk))

    pieces = _split(text)
    if not pieces:
        logger.info("ingest_source: no text for %s:%s", ct.model, source_obj.pk)
        return 0

    vectors = embed_texts(pieces)
    base_meta = extra_metadata or {}

    chunks = [
        KnowledgeChunk(
            source_type=ct,
            source_id=source_obj.pk,
            owner_id=getattr(source_obj, "owner_id", None),
            team_id=getattr(source_obj, "team_id", None),
            content=piece,
            embedding=vector,
            chunk_index=i,
            token_count=len(piece.split()),
            metadata={**base_meta, "chunk_index": i},
        )
        for i, (piece, vector) in enumerate(zip(pieces, vectors))
    ]
    written = store.upsert(chunks)
    logger.info("Ingested %s chunks for %s:%s", written, ct.model, source_obj.pk)
    return written
