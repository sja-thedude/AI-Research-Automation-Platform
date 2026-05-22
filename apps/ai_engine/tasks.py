"""AI engine async tasks: indexing, agent runs, report generation."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("neuraforge")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def index_document(self, document_id: str) -> dict:
    """Chunk + embed an extracted document into the vector store."""
    from apps.documents.models import Document

    from .services.ingestion import ingest_source

    doc = Document.objects.get(id=document_id)
    try:
        count = ingest_source(
            doc,
            doc.extracted_text,
            extra_metadata={"title": doc.title, "file_type": doc.file_type},
        )
        doc.status = Document.Status.INDEXED
        doc.save(update_fields=["status"])
        # Notify subscribers (file explorer / dashboards) over WebSocket.
        _broadcast_document_status(doc)
        return {"status": "indexed", "chunks": count}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Indexing failed for %s", document_id)
        doc.status = Document.Status.FAILED
        doc.error = str(exc)
        doc.save(update_fields=["status", "error"])
        raise self.retry(exc=exc)


@shared_task
def index_note(note_id: str) -> dict:
    """Chunk + embed a note so it becomes part of the knowledge base."""
    from apps.notes.models import Note

    from .services.ingestion import ingest_source

    note = Note.objects.get(id=note_id)
    count = ingest_source(note, f"{note.title}\n\n{note.content}", extra_metadata={"title": note.title})
    return {"status": "indexed", "chunks": count}


@shared_task
def run_agent_pipeline(task: str, owner_id: str, team_id: str | None = None) -> dict:
    """Execute the multi-agent research pipeline asynchronously."""
    from .services.agents import research_team

    ctx = research_team().run(task, owner_id=owner_id, team_id=team_id)
    final = ctx.scratchpad[-1]["output"] if ctx.scratchpad else ""
    return {"status": "done", "report": final, "transcript": ctx.scratchpad}


def _broadcast_document_status(doc) -> None:
    """Push a status update to the owner's WebSocket group (best-effort)."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"user_{doc.owner_id}",
            {
                "type": "notify",
                "event": "document.status",
                "data": {"id": str(doc.id), "status": doc.status, "title": doc.title},
            },
        )
    except Exception:  # noqa: BLE001 - notifications are non-critical
        logger.debug("WS broadcast skipped for doc %s", doc.id)
