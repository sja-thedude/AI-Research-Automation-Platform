"""AI-enhanced notes with Notion/Obsidian-style bidirectional linking.

Notes are first-class knowledge: they get embedded into the vector store (via
ai_engine) so they show up in search and RAG. NoteLink models the
[[wikilink]] graph between notes; tags group them.
"""
from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from apps.core.models import BaseModel, OwnedModel, SoftDeleteModel


class Tag(BaseModel, OwnedModel):
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=16, blank=True)

    class Meta:
        unique_together = ("owner", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Note(BaseModel, OwnedModel, SoftDeleteModel):
    title = models.CharField(max_length=300)
    content = models.TextField(blank=True)  # markdown
    tags = models.ManyToManyField(Tag, blank=True, related_name="notes")
    # Optional provenance: a note distilled from a document/conversation.
    source_document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_notes",
    )
    is_pinned = models.BooleanField(default=False)
    ai_metadata = models.JSONField(default=dict, blank=True)  # auto-tags, entities…

    chunks = GenericRelation(
        "ai_engine.KnowledgeChunk",
        content_type_field="source_type",
        object_id_field="source_id",
        related_query_name="note",
    )

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]
        indexes = [models.Index(fields=["owner", "is_pinned"])]

    def __str__(self) -> str:
        return self.title


class NoteLink(BaseModel):
    """A directed link between two notes (the knowledge-graph edge)."""

    source = models.ForeignKey(
        Note, on_delete=models.CASCADE, related_name="outgoing_links"
    )
    target = models.ForeignKey(
        Note, on_delete=models.CASCADE, related_name="incoming_links"
    )
    label = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("source", "target")

    def __str__(self) -> str:
        return f"{self.source_id} -> {self.target_id}"
