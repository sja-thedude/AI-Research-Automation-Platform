"""Document storage + ingestion-state models.

A Document owns the raw uploaded file and its extracted plain text. The
RAG-facing vector chunks live in `apps.ai_engine.KnowledgeChunk` (a unified
embedding store), keyed back to the document via a generic relation.
"""
from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel, OwnedModel, SoftDeleteModel


class Folder(BaseModel, OwnedModel):
    """Optional hierarchical organization for documents (file-explorer UI)."""

    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Document(BaseModel, OwnedModel, SoftDeleteModel):
    """An uploaded file and its processing lifecycle."""

    class FileType(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "Word"
        TXT = "txt", "Text"
        CSV = "csv", "CSV"
        XLSX = "xlsx", "Excel"
        IMAGE = "image", "Image"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        EXTRACTED = "extracted", _("Text Extracted")
        INDEXED = "indexed", _("Indexed")  # embedded into vector store
        FAILED = "failed", _("Failed")

    title = models.CharField(max_length=300)
    file = models.FileField(upload_to="documents/%Y/%m/")
    folder = models.ForeignKey(
        Folder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    file_type = models.CharField(
        max_length=10, choices=FileType.choices, default=FileType.OTHER
    )
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    # sha256 of contents — enables dedup and idempotent re-ingestion.
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    error = models.TextField(blank=True)

    # Extracted text + AI byproducts.
    extracted_text = models.TextField(blank=True)
    page_count = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=12, blank=True)
    summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Generic link to the vector chunks produced from this document.
    chunks = GenericRelation(
        "ai_engine.KnowledgeChunk",
        content_type_field="source_type",
        object_id_field="source_id",
        related_query_name="document",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["team", "status"]),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.INDEXED
