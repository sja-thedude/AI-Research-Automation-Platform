"""AI engine data layer.

* KnowledgeChunk — unified vector store (pgvector). Any source object
  (Document, Note, web page, transcript…) is chunked + embedded into rows
  here via a generic relation, so RAG retrieval is source-agnostic.
* AIAssistant — a configurable/"trainable" agent: persona, model, tools and
  a knowledge scope it may retrieve from.
* Conversation / Message — chat history with citation tracking.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from pgvector.django import HnswIndex, VectorField

from apps.core.models import BaseModel, OwnedModel

EMBED_DIM = settings.AI_SETTINGS["EMBEDDING_DIM"]


class KnowledgeChunk(BaseModel, OwnedModel):
    """A single embedded text span — the atomic unit of retrieval."""

    # Generic link to whatever produced this chunk.
    source_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    source_id = models.UUIDField()
    source = GenericForeignKey("source_type", "source_id")

    content = models.TextField()
    embedding = VectorField(dimensions=EMBED_DIM, null=True)
    chunk_index = models.PositiveIntegerField(default=0)
    token_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)  # page, heading, span…

    class Meta:
        ordering = ["source_id", "chunk_index"]
        indexes = [
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["owner"]),
            # Approximate-NN index for cosine similarity at scale.
            HnswIndex(
                name="kc_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"Chunk<{self.source_type_id}:{self.source_id}#{self.chunk_index}>"


class AIAssistant(BaseModel, OwnedModel):
    """A configurable agent users can build and 'train' on their knowledge."""

    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    system_prompt = models.TextField(
        blank=True,
        help_text="Persona / instructions prepended to every conversation.",
    )
    model = models.CharField(max_length=64, blank=True)  # defaults to platform model
    temperature = models.FloatField(default=0.2)
    # Declarative tool enablement (web_search, code, calc…) for agentic runs.
    tools = models.JSONField(default=list, blank=True)
    # Knowledge scope: which documents/folders this assistant may retrieve from.
    # Empty == all of the owner's/team's indexed knowledge.
    knowledge_scope = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name

    @property
    def resolved_model(self) -> str:
        return self.model or settings.AI_SETTINGS["CHAT_MODEL"]


class Conversation(BaseModel, OwnedModel):
    """A chat thread, optionally bound to a specific assistant."""

    title = models.CharField(max_length=300, blank=True)
    assistant = models.ForeignKey(
        AIAssistant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.title or f"Conversation<{self.id}>"


class Message(BaseModel):
    """A single turn. Citations link assistant answers back to source chunks."""

    class Role(models.TextChoices):
        SYSTEM = "system", _("System")
        USER = "user", _("User")
        ASSISTANT = "assistant", _("Assistant")
        TOOL = "tool", _("Tool")

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    # [{"chunk_id", "source_id", "title", "score", "snippet"}, …]
    citations = models.JSONField(default=list, blank=True)
    token_usage = models.JSONField(default=dict, blank=True)
    model = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:40]}"
