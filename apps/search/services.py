"""Hybrid search: semantic (vector) + full-text (Postgres) with score fusion.

* semantic  — cosine similarity over KnowledgeChunk embeddings (meaning).
* fulltext  — Postgres tsvector ranking over document text (keywords).
* hybrid    — reciprocal-rank-fusion of both, the default for best recall.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import F

from apps.ai_engine.services.retrieval import retrieve
from apps.documents.models import Document


@dataclass
class SearchHit:
    type: str  # "document" | "chunk"
    id: str
    title: str
    snippet: str
    score: float
    source_id: str | None = None


def semantic_search(query: str, *, owner_id, team_id=None, top_k=10) -> list[SearchHit]:
    hits = retrieve(query, owner_id=owner_id, team_id=team_id, top_k=top_k)
    return [
        SearchHit(
            type="chunk",
            id=h.chunk_id,
            title=h.metadata.get("title", "Untitled"),
            snippet=h.content[:280],
            score=h.score,
            source_id=h.source_id,
        )
        for h in hits
    ]


def fulltext_search(query: str, *, owner_id, team_id=None, top_k=10) -> list[SearchHit]:
    vector = SearchVector("title", weight="A") + SearchVector("extracted_text", weight="B")
    search_q = SearchQuery(query, search_type="websearch")
    qs = (
        Document.objects.filter(owner_id=owner_id)
        .annotate(rank=SearchRank(vector, search_q))
        .filter(rank__gt=0)
        .order_by("-rank")[:top_k]
    )
    return [
        SearchHit(
            type="document",
            id=str(d.id),
            title=d.title,
            snippet=(d.summary or d.extracted_text)[:280],
            score=round(float(d.rank), 4),
            source_id=str(d.id),
        )
        for d in qs
    ]


def hybrid_search(query: str, *, owner_id, team_id=None, top_k=10) -> list[SearchHit]:
    """Reciprocal Rank Fusion of semantic + full-text result lists."""
    k = 60  # RRF dampening constant
    fused: dict[str, tuple[SearchHit, float]] = {}

    for rank, hit in enumerate(semantic_search(query, owner_id=owner_id, team_id=team_id, top_k=top_k)):
        key = hit.source_id or hit.id
        score = 1.0 / (k + rank)
        fused[key] = (hit, fused.get(key, (hit, 0.0))[1] + score)

    for rank, hit in enumerate(fulltext_search(query, owner_id=owner_id, team_id=team_id, top_k=top_k)):
        key = hit.source_id or hit.id
        score = 1.0 / (k + rank)
        existing = fused.get(key)
        fused[key] = (existing[0] if existing else hit, (existing[1] if existing else 0.0) + score)

    ranked = sorted(fused.values(), key=lambda t: t[1], reverse=True)[:top_k]
    results = []
    for hit, fused_score in ranked:
        hit.score = round(fused_score, 5)
        results.append(hit)
    return results


SEARCHERS = {
    "semantic": semantic_search,
    "fulltext": fulltext_search,
    "hybrid": hybrid_search,
}


def to_dicts(hits: list[SearchHit]) -> list[dict]:
    return [asdict(h) for h in hits]
