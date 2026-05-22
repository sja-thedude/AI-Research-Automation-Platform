"""Notes async tasks: AI enrichment + re-indexing."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("neuraforge")


@shared_task
def enrich_note(note_id: str) -> dict:
    """Auto-generate tags + a one-line summary, then re-index the note."""
    from apps.ai_engine.services.summarization import SummarizationService
    from apps.ai_engine.tasks import index_note

    from .models import Note

    note = Note.objects.get(id=note_id)
    if note.content.strip():
        summary = SummarizationService().summarize(note.content, mode="short", title=note.title)
        note.ai_metadata = {**note.ai_metadata, "summary": summary}
        note.save(update_fields=["ai_metadata"])

    index_note.delay(str(note.id))
    return {"status": "enriched"}
