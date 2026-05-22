"""Async document ingestion pipeline.

    upload -> process_document (extract text)
           -> ai_engine.tasks.index_document (chunk + embed -> vector store)

Splitting extraction from embedding keeps the queues independent and lets the
embedding step retry without re-parsing the file.
"""
from __future__ import annotations

import logging

from celery import shared_task

from apps.core.utils import sha256_of_file

from .extractors import extract
from .models import Document

logger = logging.getLogger("neuraforge")


@shared_task(bind=True, max_retries=3, default_retry_delay=20)
def process_document(self, document_id: str) -> dict:
    """Extract text + metadata, then hand off to the embedding task."""
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error("process_document: document %s missing", document_id)
        return {"status": "missing"}

    doc.status = Document.Status.PROCESSING
    doc.save(update_fields=["status"])

    try:
        with doc.file.open("rb") as fh:
            doc.content_hash = sha256_of_file(fh)
            result = extract(doc.file_type, fh)

        doc.extracted_text = result.text
        doc.page_count = result.page_count
        doc.word_count = len(result.text.split())
        doc.metadata = {**doc.metadata, **result.metadata}
        doc.status = Document.Status.EXTRACTED
        doc.error = ""
        doc.save()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Extraction failed for %s", document_id)
        doc.status = Document.Status.FAILED
        doc.error = str(exc)
        doc.save(update_fields=["status", "error"])
        raise self.retry(exc=exc)

    # Hand off to the AI queue for chunking + embedding.
    from apps.ai_engine.tasks import index_document

    index_document.delay(str(doc.id))
    return {"status": "extracted", "words": doc.word_count}


@shared_task
def summarize_document(document_id: str) -> dict:
    """Generate and persist an AI summary for a document."""
    from apps.ai_engine.services.summarization import SummarizationService

    doc = Document.objects.get(id=document_id)
    summary = SummarizationService().summarize(
        doc.extracted_text, mode="long", title=doc.title
    )
    doc.summary = summary
    doc.save(update_fields=["summary"])
    return {"status": "summarized", "chars": len(summary)}
